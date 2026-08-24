import tkinter as tk
from tkinter import ttk
import threading
import queue
import time
import cv2
import numpy as np
import eBUS as eb
from API_Acuros import Acuros
import sys
try:
    import rclpy
    from rclpy.node import Node
    from cv_bridge import CvBridge
    from sensor_msgs.msg import Image
except Exception:
    print("rclpy and ROS2 must be available to run this node.", file=sys.stderr)
    raise

# ---------------------------------------------------------
# 3-sigma contrast enhancement (bit-depth agnostic)
# ---------------------------------------------------------
def contrast_stretch_3sigma(img):
    img = img.astype(np.float32)

    mean = float(np.mean(img))
    std = float(np.std(img))

    low = mean - 3.0 * std
    high = mean + 3.0 * std

    if high <= low or std == 0.0:
        return np.zeros_like(img, dtype=np.uint8)

    clipped = np.clip(img, low, high)
    stretched = (clipped - low) * (255.0 / (high - low))

    return stretched.astype(np.uint8)

# ---------------------------------------------------------
# GenICam Browser
# ---------------------------------------------------------
class GenICamBrowser(tk.Frame):
    def __init__(self, parent, cam):
        super().__init__(parent)
        self.cam = cam
        self.expanded = False
        self.build_ui()

    def build_ui(self):
        # --- Collapsible Header ---
        header = tk.Frame(self)
        header.pack(fill="x", anchor="w")

        self.toggle_btn = tk.Button(
            header,
            text="▶ GenICam Browser",
            command=self.toggle
        )
        self.toggle_btn.pack(side="left", anchor="w")

        # --- Collapsible Content ---
        self.content = tk.Frame(self)

        # Treeview with only Feature + Value
        self.tree = ttk.Treeview(
            self.content,
            columns=("value",),
            show="tree headings",
            height=20
        )

        self.tree.heading("#0", text="Feature")
        self.tree.heading("value", text="Value")

        self.tree.column("#0", width=240, anchor="w")
        self.tree.column("value", width=140, anchor="w")

        self.tree.pack(fill="both", expand=True, anchor="w")

        tk.Button(self.content, text="Refresh", command=self.refresh).pack(anchor="w")

        self.tree.bind("<Double-1>", self.on_edit)

    # -----------------------------------------------------
    # Collapsible toggle
    # -----------------------------------------------------
    def toggle(self):
        if self.expanded:
            self.content.pack_forget()
            self.toggle_btn.config(text="▶ GenICam Browser")
            self.expanded = False
        else:
            self.content.pack(fill="both", expand=True, anchor="w")
            self.toggle_btn.config(text="▼ GenICam Browser")
            self.expanded = True
            self.refresh()

    # -----------------------------------------------------
    # Refresh feature list (only AcquisitionControl + CameraHeadFeature)
    # -----------------------------------------------------
    def refresh(self):
        self.tree.delete(*self.tree.get_children())

        categories = {}

        for name in dir(self.cam):
            if not name.startswith("GIC_"):
                continue

            feature = getattr(self.cam, name)

            # Underlying PvGenParameter
            try:
                f = feature._feature
            except:
                continue

            # Category (use last element)
            try:
                category = f.GetCategory()[-1]
            except:
                continue

            # Filter categories
            if not (category.endswith("AcquisitionControl") or category.endswith("CameraHeadFeature")):
                continue

            # Type (enum → string)
            try:
                ftype_enum = f.GetType()
                ftype = self.pvgen_type_to_string(ftype_enum)
            except:
                ftype = "Unknown"

            # Value (skip commands)
            if ftype == "Command":
                val = ""
            else:
                try:
                    val = feature.getValue()
                except:
                    val = ""

            # Store feature
            if category not in categories:
                categories[category] = []
            categories[category].append((name, val))

        # Sort categories alphabetically
        for category in sorted(categories.keys()):
            parent = self.tree.insert("", "end", text=category, open=True)

            # Sort features alphabetically
            for name, val in sorted(categories[category], key=lambda x: x[0]):
                self.tree.insert(
                    parent,
                    "end",
                    iid=name,
                    text=name,
                    values=(val,)
                )

    # -----------------------------------------------------
    # Edit feature dialog
    # -----------------------------------------------------
    def on_edit(self, event):
        item = self.tree.selection()[0]

        # Skip category headers
        if self.tree.parent(item) == "":
            return

        name = item
        feature = getattr(self.cam, name)

        edit_win = tk.Toplevel(self)
        edit_win.title(f"Edit {name}")

        tk.Label(edit_win, text=name).pack()

        try:
            current = feature.getValue()
        except:
            current = ""

        entry = tk.Entry(edit_win)
        entry.insert(0, str(current))
        entry.pack()

        def apply():
            new_val = entry.get()
            try:
                feature.setValue(int(new_val))
            except:
                try:
                    feature.setValue(float(new_val))
                except:
                    try:
                        feature.setValue(new_val)
                    except Exception:
                        pass

            self.refresh()
            edit_win.destroy()

        tk.Button(edit_win, text="Apply", command=apply).pack()


# ---------------------------------------------------------
# Camera acquisition thread
# ---------------------------------------------------------
def camera_worker(cam, frame_queue, stop_event):
    # Open stream once
    stream = cam._openStream()
    cam._configureStream()

    # Configure buffers once
    buffer_list = cam._configureStreamBuffers()

    # Start acquisition once
    cam.device.StreamEnable()
    cam._startStream()

    while not stop_event.is_set():
        # Retrieve next buffer (timeout 1000 ms)
        result, pvbuffer, op_result = stream.RetrieveBuffer(1000)

        if result.IsOK() and op_result.IsOK():
            payload_type = pvbuffer.GetPayloadType()

            if payload_type == eb.PvPayloadTypeImage:
                image = pvbuffer.GetImage()
                frame = np.copy(image.GetDataPointer())  # copy to avoid reuse
                try:
                    frame_queue.put(frame, timeout=0.001)
                except queue.Full:
                    # Drop old frame, replace with newest
                    frame_queue.get_nowait()
                    frame_queue.put(frame)


        # Re-queue buffer for next frame
        stream.QueueBuffer(pvbuffer)

    # Shutdown sequence
    cam._stopStream()
    cam.device.StreamDisable()
    stream.AbortQueuedBuffers()

    # Drain buffers
    while stream.GetQueuedBufferCount() > 0:
        stream.RetrieveBuffer()

    cam._closeStream()



# ---------------------------------------------------------
# Processing thread (heavy work off GUI thread)
# ---------------------------------------------------------
def processing_worker(frame_queue, processed_queue, stop_event):
    while not stop_event.is_set():
        try:
            frame16 = frame_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        frame8 = contrast_stretch_3sigma(frame16)
        try:
            processed_queue.put(frame8, timeout=0.001)
        except queue.Full:
            processed_queue.get_nowait()
            processed_queue.put(frame8)



# ---------------------------------------------------------
# Tkinter GUI class
# ---------------------------------------------------------
class AcurosPublisher(Node):
    def __init__(self, topic: str = 'swir_sensor', period_s: float = 5.0):
        super().__init__('onsemi_swir_node')
        self.pub = self.create_publisher(Image, topic, 10)
        #self.timer = self.create_timer(period_s, self._on_timer)
        self.bridge = CvBridge()
        self.rgb = None
        self.get_logger().info(f"Publishing on '{topic}' every {period_s}s")

        self.root = tk.Tk()
        self.root.title("Acuros Live Stream")
        
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        # Canvas for image display
        self.canvas = tk.Canvas(self.root, width=640, height=512)
        self.canvas.pack()

        # FPS label
        self.fps_label = tk.Label(self.root, text="FPS: 0.0")
        self.fps_label.pack()

        # Exit button
        tk.Button(self.root, text="Exit", command=self.close).pack()

        # Camera + threading
        self.cam = Acuros()
        self.frame_queue = queue.Queue(maxsize=1)
        self.processed_queue = queue.Queue(maxsize=1)
        self.stop_event = threading.Event()

        self.worker = threading.Thread(
            target=camera_worker,
            args=(self.cam, self.frame_queue, self.stop_event),
            daemon=True
        )
        self.worker.start()

        self.proc_worker = threading.Thread(
            target=processing_worker,
            args=(self.frame_queue, self.processed_queue, self.stop_event),
            daemon=True
        )
        self.proc_worker.start()

        # Image cache to prevent Tkinter garbage-collection errors
        self.image_cache = []

        # FPS tracking
        self.frame_count = 0
        self.fps = 0.0
        self.last_fps_time = time.time()
        
        # GenICam browser panel
        browser_frame = tk.Frame(self.root)
        browser_frame.pack(side="left", fill="y", anchor="nw")
        self.browser = GenICamBrowser(browser_frame, self.cam)
        self.browser.pack(fill="y", anchor="nw")


        # Start periodic GUI update
        self.update_frame()

        self.root.mainloop()

    # -----------------------------------------------------
    # ROS timer to Publish the image 
    # -----------------------------------------------------
    def _on_timer(self):
        #if np.any(self.rgb):
        msg = self.bridge.cv2_to_imgmsg(self.rgb, encoding='passthrough')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.encoding = 'rgb8'
        self.pub.publish(msg)
    
    # -----------------------------------------------------
    # Periodic frame updater (non-blocking)
    # -----------------------------------------------------
    def update_frame(self):
        if self.stop_event.is_set():
            return
    
        # Always define frame8 first
        frame8 = None
    
        # Drain queue completely to get the newest frame
        while True:
            try:
                frame8 = self.processed_queue.get_nowait()
            except queue.Empty:
                break
    
        # If we got a frame, display it
        if frame8 is not None:
    
            # --- FPS COUNTER ---
            self.frame_count += 1
            now = time.time()
            if now - self.last_fps_time >= 1.0:
                self.fps = self.frame_count / (now - self.last_fps_time)
                self.frame_count = 0
                self.last_fps_time = now
                self.fps_label.config(text=f"FPS: {self.fps:.1f}")
            # --------------------
    
            self.rgb = cv2.cvtColor(frame8, cv2.COLOR_GRAY2RGB)
           

            success, png = cv2.imencode(".png", self.rgb)
    
            if success:
                img = tk.PhotoImage(data=png.tobytes())
                self.image_cache.append(img)
                if len(self.image_cache) > 5:
                    self.image_cache.pop(0)
                self.canvas.create_image(0, 0, anchor=tk.NW, image=img)
                 #--ROS-- Publish the image to ROS2 topic
                msg = self.bridge.cv2_to_imgmsg(self.rgb, encoding='passthrough')
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.encoding = 'rgb8'
                self.pub.publish(msg)
    
        self.root.after(10, self.update_frame)


    # -----------------------------------------------------
    # Cleanup (safe shutdown)
    # -----------------------------------------------------
    def close(self):
        # Stop threads
        self.stop_event.set()
    
        # Drain queues
        try:
            while True:
                self.frame_queue.get_nowait()
        except queue.Empty:
            pass
    
        try:
            while True:
                self.processed_queue.get_nowait()
        except queue.Empty:
            pass
    
        # Kill worker threads
        if self.worker.is_alive():
            self.worker.join(timeout=2)
    
        if self.proc_worker.is_alive():
            self.proc_worker.join(timeout=2)
    
        # Release camera hardware
        try:
            self.cam._stopStream()
        except:
            pass
    
        try:
            self.cam.device.StreamDisable()
        except:
            pass
    
        try:
            self.cam.release()
        except:
            pass
    
        # Clear Tkinter image cache
        self.image_cache.clear()
    
        # Destroy window AFTER one event cycle
        self.root.after(50, self.root.destroy)



    
# ---------------------------------------------------------
# Run viewer
# ---------------------------------------------------------
def main(argv=None):
    rclpy.init()
    node =  AcurosPublisher(topic='swir_sensor', period_s=5.0)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info('Shutting down')
        node.destroy_node()
        rclpy.shutdown()
        
if __name__ == '__main__':
    main()
