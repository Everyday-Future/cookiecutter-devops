import pytest
from unittest.mock import MagicMock, patch
from core.adapters.mechatronics.arduino_controller import \
    ArduinoController  # Assuming the class is in a file named arduino_controller.py
import pandas as pd
import serial


@pytest.fixture
def mock_serial():
    with patch('core.adapters.mechatronics.arduino_controller.serial.Serial') as mock_serial:
        yield mock_serial


@pytest.fixture
def mock_logger():
    with patch('core.adapters.mechatronics.arduino_controller.logging.getLogger') as mock_logger:
        yield mock_logger


@pytest.fixture
def arduino_controller(mock_serial, mock_logger):
    controller = ArduinoController(com_port='COM3')
    mock_serial_instance = mock_serial.return_value
    mock_serial_instance.isOpen.return_value = False
    controller.logger = mock_logger.return_value
    return controller


def test_list_serial_ports_windows(mock_serial):
    with patch('platform.system', return_value='Windows'):
        ports = ArduinoController.list_serial_ports()
        assert mock_serial.called
        assert isinstance(ports, list)


def test_list_serial_ports_mac(mock_serial):
    with patch('platform.system', return_value='Darwin'), patch('glob.glob', return_value=['/dev/tty.usbmodem']):
        ports = ArduinoController.list_serial_ports()
        assert list(set(ports)) == ['/dev/tty.usbmodem']


def test_list_serial_ports_linux(mock_serial):
    with patch('platform.system', return_value='Linux'), patch('glob.glob', return_value=['/dev/ttyUSB0']):
        ports = ArduinoController.list_serial_ports()
        assert list(set(ports)) == ['/dev/ttyUSB0']


def test_connect(arduino_controller, mock_serial):
    mock_serial_instance = mock_serial.return_value
    mock_serial_instance.isOpen.return_value = False  # Initially, it is not open
    arduino_controller.connect()
    mock_serial_instance.open.assert_called_once()
    mock_serial_instance.isOpen.return_value = True  # After connection, it should be open
    assert arduino_controller.device.isOpen()
    arduino_controller.logger.info.assert_called_with('Connected to device at COM3 with baud rate 115200 and timeout 5')


def test_connect_failure(mock_serial):
    mock_serial.side_effect = serial.SerialException
    controller = ArduinoController(com_port='COM3')
    with pytest.raises(serial.SerialException):
        controller.connect()


def test_disconnect(arduino_controller, mock_serial):
    arduino_controller.connect()
    arduino_controller.disconnect()
    mock_serial.return_value.close.assert_called_once()
    assert arduino_controller.device is None
    arduino_controller.logger.info.assert_called_with('Disconnected from device')


def test_send_command(arduino_controller, mock_serial):
    arduino_controller.connect()
    arduino_controller.device.readline.return_value = b'-1\n'
    arduino_controller.send_command('M', 10)
    arduino_controller.device.write.assert_called_once_with(b'M10')
    arduino_controller.logger.debug.assert_any_call('Sent: M10')
    arduino_controller.logger.info.assert_called_with('Command executed successfully.')


def test_send_command_failure(arduino_controller, mock_serial):
    arduino_controller.connect()
    arduino_controller.device.readline.return_value = b'-2\n'
    with pytest.raises(ValueError, match='Command execution failed.'):
        arduino_controller.send_command('M', 10)


def test_send_command_unexpected_response(arduino_controller, mock_serial):
    arduino_controller.connect()
    arduino_controller.device.readline.return_value = b'unexpected\n'
    with pytest.raises(ConnectionError, match='Received unexpected response.'):
        arduino_controller.send_command('M', 10)


def test_read_serial(arduino_controller, mock_serial):
    arduino_controller.connect()
    arduino_controller.device.readline.return_value = b'test\n'
    response = arduino_controller.read_serial()
    assert response == 'test'
    arduino_controller.logger.debug.assert_called_with('Message from ArduinoController: test')


def test_clear_serial(arduino_controller, mock_serial):
    arduino_controller.connect()
    arduino_controller.device.in_waiting = 2
    arduino_controller.device.readline.side_effect = ['test\n', 'test\n']

    def side_effect():
        arduino_controller.device.in_waiting -= 1
        return b'test\n'

    arduino_controller.device.readline.side_effect = side_effect
    arduino_controller.clear_serial()
    assert arduino_controller.device.readline.call_count == 2
    arduino_controller.logger.debug.assert_any_call('Message from ArduinoController: test')


def test_send_command_and_wait(arduino_controller, mock_serial):
    arduino_controller.connect()
    arduino_controller.device.readline.side_effect = [b'processing\n', b'System ready\n']
    with patch.object(arduino_controller, '_handle_response', side_effect=lambda x: None):
        arduino_controller.send_command_and_wait('M', 10)
    arduino_controller.logger.debug.assert_any_call('Message from ArduinoController: processing')
    arduino_controller.logger.debug.assert_any_call('Message from ArduinoController: System ready')


def test_send_command_get_csv(arduino_controller, mock_serial):
    arduino_controller.connect()
    # Mock readline to return the expected sequence of data
    arduino_controller.device.readline.side_effect = [b'1234,56\n', b'System ready\n']

    def mock_send_command(command, value=0):
        # Directly append the data to the buffer as if it was read from the device
        arduino_controller.device.readline.side_effect = [b'1234,56\n', b'System ready\n']

    # Patch the send_command method to avoid the call to _handle_response
    with patch.object(arduino_controller, 'send_command', side_effect=mock_send_command):
        df = arduino_controller.send_command_get_csv('M', 10)

    assert not df.empty
    assert df['timestamp'][0] == 1234
    assert df['value'][0] == 56
