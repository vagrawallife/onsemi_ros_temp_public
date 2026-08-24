# -*- coding: utf-8 -*-
"""
Created on Tue Jun 20 15:36:12 2023

@author: RobertStewart
"""
# conda install numpy==1.26.4 aenum opencv
import numpy as np # numpy version <= 1.26.4
from aenum import NoAlias 
import cv2

# pip install <eBUS python .whl file>
import eBUS as eb

# native packages
import time 
import os
import difflib
import math
import sys

__author__ = "SWIR Vision Systems, An onsemi Company"
__copyright__ = "Copyright (C) 2024 Robert Stewart"
__license__ = "None"

def detectDevices():
    '''
    Find available Acuros devices and return the necessary connection information.

    Returns
    -------
    acuros_device_dict : dict
        KEY : Device name (str)
        VALUE : Device IP address (str)
        
    '''
    acuros_device_dict = {}
    
    #Use the eBUS system module
    lSystem = eb.PvSystem()

    #Refresh the lSystem to get a list of interfaces
    lSystem.Find()

    #Determine if each device is an Acuros device
    for i in range( lSystem.GetInterfaceCount() ) :
        
        #Get the interface
        lInterface = lSystem.GetInterface( i )
        
        #Check the interface for devices on it
        for j in range( lInterface.GetDeviceCount() ) :
            
            #Get device info
            lDI = lInterface.GetDeviceInfo( j )
            # interface_str = str(lInterface.GetDisplayID())
            display_id_str = str(lDI.GetDisplayID())
            
            #Compare the device name to Acuros devices
            if any([dev_name in display_id_str.lower() for dev_name in ['acuros']]):
                
                # If the IP address is valid, append to valid device list
                if lDI.IsConfigurationValid():
                    acuros_device_dict[display_id_str] = lDI.GetConnectionID()
                
    return acuros_device_dict


class Acuros():
    '''
    Acuros object to interface with SWIR Vision System devices.
    See the AcurosAPI documentation for more details.
    Pass in the "verbose" flag to get more printed information during development.
    '''
    #%% Class Utils
    def __init__(self,IP_ADDRESS=None,verbose=False):
        # Class modifiers
        self.verbose = verbose
        
        # Constants
        self.BUFFER_COUNT = 16
        self.GPOMUX_FRAMESYNC = 0
        self.GPOMUX_LINESYNC = 1
        self.GPOMUX_EXPOSURE = 2
        self.ROICGAIN_LOW = 0
        self.ROICGAIN_MEDIUM = 1
        self.ROICGAIN_HIGH = 2
        self.MASTERCLOCK_LOW = 0
        self.MASTERCLOCK_HIGH = 1
        self.TESTPATTERN_OFF = 0
        self.TESTPATTERN_ON = 1
        
        # Uninitialized GIC Parameters
        self.stream = None
        self.Images = None
        self._stop = None
        self._start = None
        
        #Output properties
        self.max_rate = 100 #Hz
        
        # Uninitialized Serial Parameters
        self.IP_ADDRESS = IP_ADDRESS
        self.SerialNumber = None
        self.FPGA_Version = None
        self.FPGA_Micro_Version = None
        self.OutputMUX = None
        self.AutoExposure = None
        self.FPGA_ProcessorTemp = None
        self.TEC_Micro_Version = None
        self.Pleora_Version = None
        
        # Startup function
        self._initialize()
    
    #%% Camera Utils
    def _initialize(self):
        #Get the camera device
        success = self._getDevice()
        
        if success:
            #Test all boards
            boards_functioning = self._boardTest()
            if boards_functioning:
                #Populate hardware information
                self.FPGA_getSerialNumber()
                self.FPGA_getFPGAVersion()
                self.FPGA_getMicroVersion()
                self.TEC_getMicroVersion()
                
                #Populate and load GenICam features
                self._getDeviceParameters()
                self.Pleora_getVersion()
                
                #Enforce IEEE1588 PTP for accurate timestamping
                try:
                    self.GIC_GevIEEE1588.setValue(True)
                except: #USB3
                    pass
                
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, trace_back):
        self.release()
        
    def release(self):
        '''
        Release the camera device. Must be called to use the device with other software.

        Returns
        -------
        None.

        '''
        #Clean up communication lines, interfaces, and large variables
        if hasattr(self,'_device_adapter'): 
            del self._device_adapter
        if hasattr(self,'stream'):
            try:
                eb.PvStream.Free(self.stream)
                del self.stream
            except Exception:
                print('Stream variable exists but command could not be sent.')
        if hasattr(self,'device'):
            try:
                eb.PvDevice.Disconnect(self.device)
                eb.PvDevice.Free(self.device)
                print('\nReleased device at ',self.IP_ADDRESS)
                del self.device
            except Exception:
                print('Device variable exists but command could not be sent.')
    
    def powerCycle(self):
        '''
        TBD

        Returns
        -------
        None.

        '''
        print('Power cycle initiated...')
        self.GIC_DeviceReset.execute()
        self.release()
        time.sleep(10)
        self._initialize()
        print('Power cycled.')
        
    def loadFactoryDefaults(self):
        '''
        Loads Factory Default settings to the camera.
        Affected parameters:
                TBD

        Returns
        -------
        None.

        '''
        self._FPGA_loadFactoryDefaults()
        time.sleep(.1)
        self._TEC_loadFactoryDefaults()
        if self.verbose: 
            print('Factory defaults loaded.')
        
    def saveSettings(self):
        '''
        Saves parameters to the camera's non-volatile memory.

        Returns
        -------
        None.

        '''
        self._FPGA_saveSettings()
        time.sleep(.1)
        self._TEC_saveSettings()
        if self.verbose: 
            print('Settings saved to nonvolatile memory.')
    
    def _getDeviceParameters(self):
        parameters = self.device.GetParameters()
        parameters.SetBooleanValue('PixelBusDataValidEnabled',True)
        parameters.SetEnumValue('TestPattern', self.TESTPATTERN_OFF)
        self._stop = parameters.Get('AcquisitionStop')
        self._start = parameters.Get('AcquisitionStart')
        num_params = parameters.GetCount()
        stream_commands = {'stop': self._stop,
                           'start': self._start,
                           'disable': self.device.StreamDisable,
                           'enable': self.device.StreamEnable}
            
        if self.verbose: 
            print('Refreshing ',num_params,' GenICam parameters...')
        count = 0
        for parameter in parameters:
            count+=1
            if parameter != None: #apparently there is one parameter with no name
                try:
                    name = parameter.GetName()[-1]
                    if not hasattr(self,'GIC_'+name):
                        self.__setattr__('GIC_'+name,self._GenICam(parameter,stream_commands,self.verbose)) 
                except Exception as exc:
                    if self.verbose:
                        print('Could not create GIC attribute for ',parameter,'\n',exc)
            if count % 10 == 0: 
                if self.verbose: 
                    print('\x1b[2K\r',end='') #Erase line
                if self.verbose: 
                    print(count,'/',num_params,end='')
            if count>num_params:
                if self.verbose: 
                    print('\x1b[2K\r',end='')
                if self.verbose: 
                    print('-GenICam parameters refreshed.\n')
                break
    
    def _getDevice(self):
        if not self.IP_ADDRESS:
            #Begin a search loop and return the first one
            if self.verbose:
                print('Searching for Acuros devices...')
            acuros_device_dict = detectDevices()
            dev = list(acuros_device_dict.keys())[0]
            self.IP_ADDRESS = acuros_device_dict[dev]
        
        # Connect to the GEV or U3V Device
        print(f'\nConnecting to device at {self.IP_ADDRESS}\n')
        result, self.device = eb.PvDevice.CreateAndConnect(self.IP_ADDRESS) 
        if not result.IsOK():
            print("Unable to connect to device")
            return False
        else:
            return True
        
    def _stopStream(self):
        self._stop.Execute()
        
    def _startStream(self):
        self._start.Execute()
        
    def _openStream(self):
        # Open stream to the GigE Vision or USB3 Vision device
        result, self.stream = eb.PvStream.CreateAndOpen(self.IP_ADDRESS)
        if self.stream == None:
            print(f"Unable to stream from device. {result.GetCodeString()} ({result.GetDescription()})")
        return self.stream
    
    def _closeStream(self):
        try: 
            self.stream.Close()
        except Exception: pass
    
    def _configureStream(self):
        # If this is a GigE Vision device, configure GigE Vision specific streaming parameters
        if isinstance(self.device, eb.PvDeviceGEV):
            # Negotiate packet size
            self.device.NegotiatePacketSize()
            # Configure device streaming destination
            self.device.SetStreamDestination(self.stream.GetLocalIPAddress(), self.stream.GetLocalPort())
            
    def _configureStreamBuffers(self):
        buffer_list = []
        # Reading payload size from device
        size = self.device.GetPayloadSize()

        # Use BUFFER_COUNT or the maximum number of buffers, whichever is smaller
        buffer_count = self.stream.GetQueuedBufferMaximum()
        if buffer_count > self.BUFFER_COUNT:
            buffer_count = self.BUFFER_COUNT

        # Allocate buffers
        for _ in range(buffer_count):
            # Create new pvbuffer object
            pvbuffer = eb.PvBuffer()
            # Have the new pvbuffer object allocate payload memory
            pvbuffer.Alloc(size)
            # Add to external list - used to eventually release the buffers
            buffer_list.append(pvbuffer)
        
        # Queue all buffers in the stream
        for pvbuffer in buffer_list:
            self.stream.QueueBuffer(pvbuffer)
        # print(f"Created {buffer_count} buffers")
        return buffer_list
    
    #%% GenICam Class
    class _GenICam():
        '''
        Internal class to dynamically generate GenICam features from the camera.
        '''
        _settings_ = NoAlias
        
        def __new__(cls,feature,stream_commands,verbose=False):
            member = super().__new__(cls)
            return member
        
        def __init__(self,feature,stream_commands,verbose=False):
            self._feature = feature
            self.name = self._feature.GetName()[-1]
            self.value=None
            self.verbose=verbose
            self.type = self._feature.__class__
            self._type_enum = self._feature.GetType()[-1]
            self._stream_commands = stream_commands
            
            if all([self._type_enum != class_type for class_type in [eb.PvGenTypeCommand,eb.PvGenTypeUndefined,eb.PvGenTypeRegister]]):
                self.value = self.getValue()
                
                if any([self._type_enum == class_type for class_type in [eb.PvGenTypeInteger,eb.PvGenTypeFloat,eb.PvGenTypeRegister]]):
                    self.minimum = self._feature.GetMin()[-1]
                    self.maximum = self._feature.GetMax()[-1]
                    if self._type_enum == eb.PvGenTypeInteger: 
                        self.increment = self._feature.GetIncrement()[-1]
                    self.units = self._feature.GetUnit()[-1]
                elif self._type_enum == eb.PvGenTypeString:
                    try: 
                        self.maxlength = self._feature.GetMaxLength[-1]
                    except Exception: 
                        self.maxlength = None
            
        def getValue(self):
            '''
            

            Returns
            -------
            active_val : TYPE
                DESCRIPTION.

            '''
            if all([self._type_enum != class_type for class_type in [eb.PvGenTypeCommand,eb.PvGenTypeUndefined,eb.PvGenTypeRegister]]):
                if any([self._type_enum == class_type for class_type in [eb.PvGenTypeInteger,
                                                              eb.PvGenTypeBoolean,
                                                              eb.PvGenTypeString,
                                                              eb.PvGenTypeFloat]]):
                    _,active_val = self._feature.GetValue()
                elif self._type_enum == eb.PvGenTypeEnum:
                    _,active_val = self._feature.GetValueString()
                return active_val
            else:
                print('Failed to get value; ',self.name,' is a command.')
                return None
        
        def setValue(self,val):
            '''
            

            Parameters
            ----------
            val : TYPE
                DESCRIPTION.

            Returns
            -------
            None.

            '''
            #If the class type accepts values
            if all([self._type_enum != class_type for class_type in [eb.PvGenTypeCommand,eb.PvGenTypeUndefined]]):
                
                #If it is unwritable, try to stop the stream and continue
                if not self._feature.IsWritable()[-1]:
                    try: 
                        self._stream_commands['stop'].Execute()
                    except Exception as e:
                        print(e)
                    self._stream_commands['disable']()
                    
                    #If it is still unwritable, exit with warning
                    if not self._feature.IsWritable()[-1]:
                        print(f'GIC_{self.name} feature has not yet been loaded, or it is not writable.')
                        return
                #Set value
                result = self._feature.SetValue(val)
                
                #Check result
                if result.IsOK():
                    self.value = val
                    if self.verbose:
                        print(f'GIC_{self.name} setValue success')
                else:
                    print('-ERROR: ',result.GetCodeString(),'\n\t',result.GetDescription())
                    test_conditions = [self._feature.IsAvailable,
                                       self._feature.IsWritable,
                                       self._feature.IsReadable,
                                       self._feature.IsStreamable]
                    [print('\tFailed ',function.__name__,' test.') for function in test_conditions if function==False]
                
                #Re-enable stream in case it was disabled
                self._stream_commands['enable']()
                
            else:
                print('Failed to set value; ',self.name,' is a command.')
                    
        def execute(self):
            '''
            

            Raises
            ------
            Exception
                DESCRIPTION.

            Returns
            -------
            None.

            '''
            if self._type_enum == eb.PvGenTypeCommand:
                result = self._feature.Execute()
                if result == eb.PV_OK:
                    while not self._feature.IsDone():
                        time.sleep(.01)
                    return
                else: raise Exception
            else:
                print('Failed to execute; ',self.name,' is not a command.')
        
        def __int__(self):
            return self.value
        
        def __str__(self):
            return str(self.value)
    
    #%% Image Acquisition
    
    def getImages(self,num_images,save=False):
        '''
        

        Parameters
        ----------
        num_images : TYPE
            DESCRIPTION.
        save : TYPE, optional
            DESCRIPTION. The default is False.

        Returns
        -------
        None.

        '''
        self._openStream()
        self._configureStream()
        buffer_list = self._configureStreamBuffers()
        self._imageAcquisition(num_images=num_images,save=save)
        buffer_list.clear()
        self._closeStream()
        
    def _imageAcquisition(self,num_images=1,save=False):
        # Get device parameters need to control streaming
        #Set up image variables
        self.Images = np.zeros(shape=[num_images,self.GIC_Height.value,self.GIC_Width.value],dtype=np.uint16)

        errors = []
        warnings = []

        # Enable streaming and send the AcquisitionStart command
        self.device.StreamEnable()
        self._startStream()
        
        for i in range(num_images):
            # print(i,'of',num_images,end='')
            # Retrieve next pvbuffer
            result, pvbuffer, operational_result = self.stream.RetrieveBuffer(1000)
            if result.IsOK():
                if operational_result.IsOK():
                    # This is where you process the pvbuffer.
                    # ---------------------------------------
                    
                    payload_type = pvbuffer.GetPayloadType()
                    if payload_type == eb.PvPayloadTypeImage:
                        image = pvbuffer.GetImage()
                        image_data = image.GetDataPointer()
                        
                        #Attach to the class
                        self.Images[i] = image_data
                        
                        if save:
                            save_path = os.path.join(os.environ['USERPROFILE'],'Downloads','Image'+str(i)+'.png')
                            cv2.imwrite(save_path,image_data)

                    else:
                        warnings.append[i,str(payload_type)]
                else:
                    # Non OK operational result
                    errors.append([i,str(operational_result.GetCodeString())])
                # Re-queue the pvbuffer in the stream object
                self.stream.QueueBuffer(pvbuffer)
            else:
                # Retrieve pvbuffer failure
                errors.append([i,str(result.GetCodeString())])
        # print('\x1b[2K\r',end='\n') #Erase line

        # Tell the device to stop sending images.
        self._stopStream()

        # Disable streaming on the device
        self.device.StreamDisable()

        # Abort all buffers from the stream and dequeue
        self.stream.AbortQueuedBuffers()
        while self.stream.GetQueuedBufferCount() > 0:
            result, pvbuffer, lOperationalResult = self.stream.RetrieveBuffer()
            
        if len(errors) > 0 and self.verbose:
            print('Non-Fatal Errors: Img ResultCode')
            [print('                 ',err) for err in errors]
        if len(warnings) > 0 and self.verbose:
            print('Warnings: Img ResultCode')
            [print('                    ',warn) for warn in warnings]
            
    #%% Serial Communication Helper Functions
    
    def _getSerialBoard(self,board='FPGA',RxBufferSize=None,clear=True):
        # Get device parameters need to control streaming
        params = self.device.GetParameters()
        
        SERIAL_SPEED = "Baud115200" 
        SERIAL_STOPBITS = "One"
        SERIAL_PARITY   = "None"
        SERIAL_BULKLOOPBACK = False
        
        if board.lower() == 'fpga':
            interface = eb.PvDeviceSerialBulk0
            SERIAL_BULKSELECTOR = 'Bulk0'
            SERIAL_BULKMODE = 'UART'
            
        elif board.lower() == 'usrt':
            interface = eb.PvDeviceSerialBulk1
            SERIAL_BULKSELECTOR = 'Bulk1'
            SERIAL_BULKMODE = 'USRT'
            params.SetEnumValue('BulkSystemClockDivider','By2')
            
        elif board.lower() == 'tec':
            interface = eb.PvDeviceSerialBulk2
            SERIAL_BULKSELECTOR = 'Bulk2'
            SERIAL_BULKMODE = 'UART'
    
        # Configure serial port
        # Done directly on the device GenICam interface, not the serial port! 
        if params.GetEnumValueString('BulkSelector') != SERIAL_BULKSELECTOR:
            params.SetEnumValue("BulkSelector" ,SERIAL_BULKSELECTOR)
        if params.GetEnumValueString("BulkMode") != SERIAL_BULKMODE:
            params.SetEnumValue("BulkMode", SERIAL_BULKMODE)
        if params.GetEnumValueString("BulkBaudRate") != SERIAL_SPEED:
            params.SetEnumValue("BulkBaudRate", SERIAL_SPEED)
        if params.GetEnumValueString("BulkNumOfStopBits") != SERIAL_STOPBITS:
            params.SetEnumValue("BulkNumOfStopBits", SERIAL_STOPBITS)
        if params.GetEnumValueString("BulkParity") != SERIAL_PARITY:
            params.SetEnumValue("BulkParity", SERIAL_PARITY)
    
        # For this test to work without attached serial hardware we disable the port loop back
        if params.GetBooleanValue("BulkLoopback") != SERIAL_BULKLOOPBACK:
            params.SetBooleanValue("BulkLoopback", SERIAL_BULKLOOPBACK)
    
        #  Open serial port
        port = eb.PvDeviceSerialPort()
        device_adapter = eb.PvDeviceAdapter(self.device)
        if eb.PvDeviceSerialPort.IsSupported(device_adapter, interface):
            result = port.Open(device_adapter, interface)
            if not result.IsOK():
                print(f'Unable to open serial port on device: {result.GetCodeString()} {result.GetDescription()}')
                return False
            if clear:
                if RxBufferSize:
                    port.SetRxBufferSize(RxBufferSize)    
                else:
                    port.FlushRxBuffer()
            return port,device_adapter
        print('Selected serial bulk interface is not supported:',interface)
        del device_adapter
        return None
        
    def _boardTest(self):
        results = {}
        #FPGA
        #Check FPGA for communication
        self._FPGA_setTestWord(10)
        results['FPGA'] = self._FPGA_getTestWord(10)
        #Check FPGA for errors
        results.update(self._FPGA_getSystemStatus())
        
        #FPGA uC
        #Check FPGA uC for communication
        self._FPGA_setMicroTestWord(20)
        results['FPGA uC'] = self._FPGA_getMicroTestWord(20)
        
        #TEC
        #Check TEC for communication
        self._TEC_setTestWord(30)
        results['TEC'] = self._TEC_getTestWord(30)
        
        if any([result != 0 for key,result in results.items()]):
            print('A board is not functioning correctly')
            print(results)
            return False
        else:
            return True
        
    def _formatCommand(self,comlsb,commsb,message=None,board='FPGA'):
        if message == None: message = ['0x00','0x00']
        
        #Calculate message size
        if len(message) >=3: msgsizeminus1 = hex(len(message)-1)
        else: msgsizeminus1 = '0x01'
        if len(message) == 1:
            message.append('0x00')
        tc_msgsizeminus1 = self._twosComplement(int(msgsizeminus1,0), 8)
        # print()
        # print('Message size - 1: ',tc_msgsizeminus1)
    
        #Get LSB
        msgsizeminus1lsb = tc_msgsizeminus1 & self._twosComplement(int('0xff',0), 8)
        # print('Message size - 1 LSB: ',msgsizeminus1lsb)
        
        #Get MSB
        msgsizeminus1msb = (tc_msgsizeminus1 >> 8) & self._twosComplement(int('0xff',0), 8)
        # print('Message size - 1 MSB: ',msgsizeminus1msb)
        # print()
        
        #UART Command Protocol
        uartcmd = []
        uartcmd.append(int('0x02',0)) #STX
        uartcmd.append(msgsizeminus1lsb) #Message Size - 1 LSB
        uartcmd.append(msgsizeminus1msb) #Message Size - 1 MSB
        uartcmd.append(int(comlsb,0)) #Command LSB
        uartcmd.append(int(commsb,0)) #Command MSB
        # Append message bytes to end of vector
        # Check whether it is hex format or already an integer
        if type(message[0]) == str:
            [uartcmd.append(int(message_part,0)) for message_part in message] 
        else:
            uartcmd = uartcmd+message
        uartcmd.append(int('0x00',0)) #Append one empty byte
        if board.lower() == 'tec':
            uartcmd.append(int('0x00',0)) #Append one empty byte
        
        if uartcmd[3] == int('0x1a',0): pass #Exit?
        
        return np.array(uartcmd,dtype='uint8')

    def _writeCommand(self,port,command):
        result, bytes_written = port.Write(command)
        start = time.perf_counter()
        while not result.IsOK():
            if bytes_written!=len(command):
                print('Not all bytes of the command were written to the port.')
            if time.perf_counter()-start > 5:
                print('Timeout while waiting for serial command to be written to the port.')
                break
            
        return bytes_written

    def _readEcho(self,port,decode=True,size=7,timeout=3000):
        # echo = np.zeros(size, dtype= np.uint8)
        total_bytes_read = 0
        
        while total_bytes_read < size:
            bytes_read = 0
            # result,echo[total_bytes_read:size],bytes_read = port.Read(size-total_bytes_read,5000)
            result,echo,bytes_read = port.Read(size-total_bytes_read,timeout)

            # End of real Read code
            if result.GetCode() == eb.PV_TIMEOUT:
                print('Timeout while reading the echo inside the function ',sys._getframe(1).f_code.co_name)
                return eb.PV_TIMEOUT
                # Increments read head
            total_bytes_read += bytes_read
        # Validate answer
        if not total_bytes_read == size and len(echo)!=size:
            # Did not receive all expected bytes
            print(f'Only received {total_bytes_read} out of {size} bytes')
            
        else:
            # check echo for success
            if int(echo[0]) == 2 and echo[1] == 1 and echo[2] == 0:
                # Success for a 2 byte number
                pass
            elif int(echo[0]) == 2 and echo[1] == 3 and echo[2] == 0:
                # Success for a 4 byte number, such as FPGA_getSerialNumber()
                pass
            else:
                print('Unexpected echo: ', echo,'inside the function ',sys._getframe(1).f_code.co_name,'\n')
        if decode:
            try:
                # parse echo
                msg_lsb = echo[3]
                msg_msb = echo[4]
                echo_val = msg_msb << 8 | msg_lsb #decode two bytes
            except Exception:
                echo_val = None
        else:
            echo_val = echo[3:]
        # print(echo_val)
        return echo_val

    def _twosComplement(self, val, bits):
        """compute the 2's complement of int value val"""
        if (val & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
            val = val - (1 << bits)        # compute negative value
        return val                         # return positive value as is
    
    def _integerToHexList(self,integer,msg_length=1):
        std_hex = hex(integer).replace('0x','')
        std_hex = '0'*(2*msg_length-len(std_hex))+std_hex
        pairs = ['0x'+std_hex[i:i+2] for i in range(0,len(std_hex),2)]
        return pairs
    
    #%% FPGA Functions
    
    def FPGA_getSerialNumber(self):
        port, device_adapter = self._getSerialBoard('FPGA')
        
        commandLSB = '0x1e'
        commandMSB = '0x02'
            
        command = self._formatCommand(commandLSB,commandMSB)
        _ = self._writeCommand(port, command)
        echo = self._readEcho(port, decode=False).tolist()
        # echo.reverse()
        echo = [hex(item) for item in echo]
        echo = ''.join(echo).replace('0x','')
            
        self.SerialNumber = int('0x'+echo,0)
        
        port.Close();del device_adapter
        return self.SerialNumber
    
    def FPGA_getFPGAVersion(self):
        '''
        Query the FPGA for the FPGA version.

        Returns
        -------
        int
            FPGA version.

        '''
        port, device_adapter = self._getSerialBoard('FPGA')
        
        commandLSB = '0x00'
        commandMSB = '0x01'
            
        command = self._formatCommand(commandLSB,commandMSB)
        _ = self._writeCommand(port, command)
        self.FPGA_Version = self._readEcho(port)
        port.Close();del device_adapter
        return self.FPGA_Version
    
    def FPGA_getMicroVersion(self):
        '''
        Query the FPGA for the uC version.

        Returns
        -------
        int
            uC Version.

        '''
        port, device_adapter = self._getSerialBoard('FPGA')
        
        commandLSB = '0x01'
        commandMSB = '0x01'
            
        command = self._formatCommand(commandLSB,commandMSB)
        _ = self._writeCommand(port, command)
        self.FPGA_Micro_Version = self._readEcho(port)
        port.Close();del device_adapter
        return self.FPGA_Micro_Version
        
    def FPGA_setNUCEnable(self,val):
        '''
        DEPRECATED. This command should only be used to set the value to 0 now, in case of malfunction.
        Use the GIC_DnucEnable feature instead of this.

        Parameters
        ----------
        val : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        '''
        
        commandLSB = '0x0e'
        commandMSB = '0x00'
        
        val_keys = ['0Off','1OffsetOn','2GainOn','3OffsetOnGainOn']
        # val = self._findClosestInput(val,val_keys) #returns int
        val = 0
        
        val = val << 8
        
        message = self._integerToHexList(val,msg_length=2)
            
        command = self._formatCommand(commandLSB,commandMSB,message)
        port, device_adapter = self._getSerialBoard('FPGA')
        _ = self._writeCommand(port, command)
        _ = self._readEcho(port)
        port.Close();del device_adapter
        
    def FPGA_getNUCEnable(self):
        '''
        DEPRECATED. Use the GIC_DnucEnable feature instead of this.

        Returns
        -------
        echo : TYPE
            DESCRIPTION.

        '''
        commandLSB = '0x0e'
        commandMSB = '0x01'
        
        command = self._formatCommand(commandLSB,commandMSB)
        port, device_adapter = self._getSerialBoard('FPGA')
        _ = self._writeCommand(port, command)
        echo = self._readEcho(port)
        
        port.Close();del device_adapter
        return echo
    
    def FPGA_setAutoExposure(self,val):
        '''
        

        Parameters
        ----------
        val : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        '''
        #Determines revision number of the uC FW. 
        #   X46 and lower one Vdet.
        #   X47 and greater has a Vdet per gain
        #   Dataray has 4 digit uC numbering
        uC_version = str(self.FPGA_Micro_Version)
        if (len(uC_version)>3)|(int(uC_version[1:]) <= 46):
            print('ERROR: Cannot set AutoExposure with this uC FW.')
        else:
            self._FPGA_setAutoExposure(val)
            
    def FPGA_getAutoExposure(self):
        '''
        

        Returns
        -------
        control : TYPE
            DESCRIPTION.

        '''
        #Determines revision number of the uC FW. 
        #   X46 and lower one Vdet.
        #   X47 and greater has a Vdet per gain
        #   Dataray has 4 digit uC numbering
        uC_version = str(self.FPGA_Micro_Version)
        if (len(uC_version)>3)|(int(uC_version[1:]) <= 46):
            print('ERROR: Cannot read AutoExposure with this uC FW.')
            control = None
        else:
            control = self._FPGA_getAutoExposure()
        return control
    
    def FPGA_getMicroTestWord(self,val):
        port, device_adapter = self._getSerialBoard('FPGA')
        
        commandLSB = '0x09'
        commandMSB = '0x02'
            
        command = self._formatCommand(commandLSB,commandMSB)
        _ = self._writeCommand(port, command)
        echo_val = self._readEcho(port)     
        
        port.Close(); del device_adapter
        
        #Verify
        if echo_val == val:
            if self.verbose: print('Successfully read; FPGA uC TestWords match.')
            return 0
        else:
            print('FPGA uC TestWord did not match. Echoed ',echo_val,' but expected response was ',val,'.')
            return 1
    
    def _FPGA_setOutputMux(self,outputmux):
        port, device_adapter = self._getSerialBoard('FPGA')
        
        commandLSB = '0x0c'
        commandMSB = '0x00'
        
        keys = ['0HRAMP_1TAP',
                '1HRAMP_2TAP',
                '2VRAMP_1TAP',
                '3VRAMP_2TAP',
                '4FRAME_1TAP',
                '5FRAME_2TAP']
        self.OutputMUX = int(difflib.get_close_matches(outputmux,keys,cutoff=.1)[0][0])
        
        message = self._integerToHexList(self.OutputMUX,msg_length=1)
            
        command = self._formatCommand(commandLSB,commandMSB,message)
        _ = self._writeCommand(port, command)
        _ = self._readEcho(port)
        port.Close();del device_adapter
        
    def FPGA_getOutputMux(self):
        port, device_adapter = self._getSerialBoard('FPGA')
        
        commandLSB = '0x0c'
        commandMSB = '0x01'
            
        command = self._formatCommand(commandLSB,commandMSB)
        _ = self._writeCommand(port, command)
        echo = self._readEcho(port)
        
        #Map
        if echo == 0:
            self.OutputMUX = self.OUTPUTMUX_HRAMP_1TAP
        elif echo == 1:
            self.OutputMUX = self.OUTPUTMUX_HRAMP_2TAP
        elif echo == 2:
            self.OutputMUX = self.OUTPUTMUX_VRAMP_1TAP
        elif echo == 3:
            self.OutputMUX = self.OUTPUTMUX_VRAMP_2TAP
        elif echo == 4:
            self.OutputMUX = self.OUTPUTMUX_FRAME_1TAP
        elif echo == 5:
            self.OutputMUX = self.OUTPUTMUX_FRAME_2TAP
            
        port.Close();del device_adapter
        return self.OutputMUX
        
    #%% FPGA Hidden Functions
        
    def _FPGA_setTestWord(self,val):
        port, device_adapter = self._getSerialBoard('FPGA')
        
        commandLSB = '0x02'
        commandMSB = '0x00'
        
        #Clamp
        val = max(0,min(65535,val))
        
        hexpair = self._integerToHexList(val,msg_length=2)
        
        #setTestWord documentation is incorrect - must flip the hex pair
        hexpair.reverse()
            
        command = self._formatCommand(commandLSB,commandMSB,hexpair)
        _ = self._writeCommand(port, command)
        _ = self._readEcho(port)
        
        port.Close(); del device_adapter
        
    def _FPGA_getTestWord(self,val):
        port, device_adapter = self._getSerialBoard('FPGA')
        
        commandLSB = '0x02'
        commandMSB = '0x01'
            
        command = self._formatCommand(commandLSB,commandMSB)
        _ = self._writeCommand(port, command)
        echo_val = self._readEcho(port)     
        
        port.Close(); del device_adapter
        
        #Verify
        if echo_val == val:
            if self.verbose: print('Successfully read; FPGA TestWords match.')
            return 0
        else:
            print('FPGA TestWord did not match. Echoed ',echo_val,' but expected response was ',val,'.')
            return 1
        
    def _FPGA_setMicroTestWord(self,val):
        port, device_adapter = self._getSerialBoard('FPGA')
        
        commandLSB = '0x08'
        commandMSB = '0x02'
        
        #Clamp
        val = max(0,min(65535,val))
        
        hexpair = self._integerToHexList(val,msg_length=2)
        
        #setTestWord documentation is incorrect - must flip the hex pair
        hexpair.reverse()
            
        command = self._formatCommand(commandLSB,commandMSB,hexpair)
        _ = self._writeCommand(port, command)
        _ = self._readEcho(port)
        
        port.Close(); del device_adapter
    
    def _FPGA_getMicroTestWord(self,val):
        port, device_adapter = self._getSerialBoard('FPGA')
        
        commandLSB = '0x09'
        commandMSB = '0x02'
            
        command = self._formatCommand(commandLSB,commandMSB)
        _ = self._writeCommand(port, command)
        echo_val = self._readEcho(port)     
        
        port.Close(); del device_adapter
        
        #Verify
        if echo_val == val:
            if self.verbose: print('Successfully read; FPGA uC TestWords match.')
            return 0
        else:
            print('FPGA uC TestWord did not match. Echoed ',echo_val,' but expected response was ',val,'.')
            return 1
    
    def _FPGA_setAutoExposure(self,AEcontrol):
        '''
        Turns autoexposure on and off.
    
        AEcontrol = 0;	Off
        AEcontrol = 1;	On
        '''
        
        port, device_adapter = self._getSerialBoard('FPGA')
        
        commandLSB = '0x24'
        commandMSB = '0x00'
        
        message = self._integerToHexList(AEcontrol,msg_length=1)
            
        command = self._formatCommand(commandLSB,commandMSB,message)
        _ = self._writeCommand(port, command)
        _ = self._readEcho(port)
        port.Close();del device_adapter
        
        self.AutoExposure = AEcontrol
        
    def _FPGA_getAutoExposure(self):
        '''
        Returns the state of the autoexposure control.
    
        AEcontrol = 0;	Off
        AEcontrol = 1;	On
        '''
        port, device_adapter = self._getSerialBoard('FPGA')
        
        commandLSB = '0x24'
        commandMSB = '0x01'
        
        command = self._formatCommand(commandLSB,commandMSB)
        _ = self._writeCommand(port, command)
        self.AutoExposure = self._readEcho(port)
        
        port.Close();del device_adapter
        return self.AutoExposure
        
    def _FPGA_getSystemStatus(self):
        port, device_adapter = self._getSerialBoard('FPGA')
        
        commandLSB = '0x17'
        commandMSB = '0x02'
        
        command = self._formatCommand(commandLSB,commandMSB)
        _ = self._writeCommand(port, command)
        echo = self._readEcho(port)
        binary = format(echo,'016b')
        statuses = {
            'DDR Calibration':int(binary[-1]),
            'FPGA Configuration':int(binary[-2]),
            'PLL Locked':int(binary[-3]),
            'ROIC Register Readback':int(binary[-4]),
            'Processer board over temp (90C)':int(binary[-5]),
            'Processer board temperature monitor init':int(binary[-6])
            }
        fail=1
        [print(check,' failed') for check,status in statuses.items() if status == fail]
        
        port.Close();del device_adapter
        return statuses
        
    #%% TEC Functions
        
    def TEC_getMicroVersion(self):
        '''
        
    
        Returns
        -------
        TYPE
            DESCRIPTION.
    
        '''
        port, device_adapter = self._getSerialBoard('TEC')
        
        commandLSB = '0x01'
        commandMSB = '0x01'
            
        command = self._formatCommand(commandLSB,commandMSB)
        _ = self._writeCommand(port, command)
        self.TEC_Micro_Version = self._readEcho(port)
        
        port.Close();del device_adapter
        return self.TEC_Micro_Version
    
    def TEC_setTempSetpoint(self,val):
        '''
        
    
        Parameters
        ----------
        val : TYPE
            DESCRIPTION.
    
        Returns
        -------
        None.
    
        '''
        port, device_adapter = self._getSerialBoard('TEC')
        
        commandLSB = '0x04'
        commandMSB = '0x00'
        
        #Clamp
        val = int(max(10,min(45,val)))
        message = self._integerToHexList(val,msg_length=1)
        command = self._formatCommand(commandLSB,commandMSB,message)
        _ = self._writeCommand(port, command)
        _ = self._readEcho(port)
        
        port.Close();del device_adapter
    
    def TEC_getTempSetpoint(self):
        '''
        
    
        Returns
        -------
        setpoint : TYPE
            DESCRIPTION.
    
        '''
        port, device_adapter = self._getSerialBoard('TEC')
        
        commandLSB = '0x04'
        commandMSB = '0x01'
            
        command = self._formatCommand(commandLSB,commandMSB)
        _ = self._writeCommand(port, command)
        setpoint = self._readEcho(port)
        
        port.Close();del device_adapter
        return setpoint
    
    def TEC_getTemperature(self):
        '''
        
    
        Returns
        -------
        temp : TYPE
            DESCRIPTION.
    
        '''
        port, device_adapter = self._getSerialBoard('TEC')
        
        commandLSB = '0x05'
        commandMSB = '0x01'
            
        command = self._formatCommand(commandLSB,commandMSB)
        _ = self._writeCommand(port, command)
        ADC_val = self._readEcho(port)
        
        a1 = .003354
        b1 = .000257
        voltage = (3.3*ADC_val)/1024
        temp = round(1/(a1+b1*math.log(voltage/(1.5-voltage)))-273,2)
        
        port.Close();del device_adapter
        return temp
        
    def TEC_getControllerState(self):
        '''
        
    
        Returns
        -------
        echo : TYPE
            DESCRIPTION.
    
        '''
        port, device_adapter = self._getSerialBoard('TEC')
        
        commandLSB = '0x07'
        commandMSB = '0x01'
            
        command = self._formatCommand(commandLSB,commandMSB)
        _ = self._writeCommand(port, command)
        echo = self._readEcho(port)
        
        port.Close();del device_adapter
        return echo
    
    #%% TEC Hidden Functions
    
    def _TEC_setTestWord(self,val):
        port, device_adapter = self._getSerialBoard('TEC')
        
        commandLSB = '0x02'
        commandMSB = '0x00'
        
        #Clamp
        val = max(0,min(65535,val))
        
        hexpair = self._integerToHexList(val,msg_length=2)
        
        #setTestWord documentation is incorrect - must flip the hex pair
        hexpair.reverse()
            
        command = self._formatCommand(commandLSB,commandMSB,hexpair,board='TEC')
        _ = self._writeCommand(port, command)
        _ = self._readEcho(port)
        
        port.Close(); del device_adapter
        
    def _TEC_getTestWord(self,val):
        port, device_adapter = self._getSerialBoard('TEC')
        
        commandLSB = '0x02'
        commandMSB = '0x01'
            
        command = self._formatCommand(commandLSB,commandMSB,board='TEC')
        _ = self._writeCommand(port, command)
        echo_val = self._readEcho(port)
        
        port.Close();del device_adapter
        
        #Verify
        if echo_val == val:
            if self.verbose: print('Successfully read; TEC TestWord match.')
            return 0
        else:
            print('TEC TestWord did not match. Echoed ',echo_val,' but expected response was ',val,'.')
            return 1
        
    #%% Pleora Wrapper Functions
    
    def Pleora_getVersion(self):
        '''
        
    
        Returns
        -------
        TYPE
            DESCRIPTION.
    
        '''
        model_name = self.GIC_DeviceModelName.value
        self.Pleora_Version = int(model_name.split('.')[-1])
        return self.Pleora_Version
    
    #%% General Helper Functions
    
    def _findClosestInput(self,orig,keys):
        #Helper function to avoid using enumerations and allow string inputs
        
        #If integer, return integer
        if isinstance(orig,int): 
            if any([orig == int(key[0]) for key in keys]): return orig
            else: orig = str(orig) #if no integer match, convert to string for parsing
            
        #If string with an integer, return integer
        if orig[0].isdigit() and any([orig[0] == key[0] for key in keys]): return int(orig[0])
        #If plain string, return closest match to the keys
        else:
            keys = [key.lower() for key in keys]
            orig = orig.lower()
            try:
                return int(difflib.get_close_matches(orig,keys,cutoff=0.01)[0][0])
            except IndexError as exc:
                raise Exception('No match was found for the input value of '+str(orig)+'in the keys:'+str(keys)) from exc
    
#%% Test
if __name__ == '__main__':
    try:
        dev_dict = detectDevices()
        dev = list(dev_dict.keys())[0]
        ip = dev_dict[dev]
        cam = Acuros(ip,verbose=False)
    except Exception as e:
        print(e)
    finally:
        if 'cam' in locals():
            cam.release()

