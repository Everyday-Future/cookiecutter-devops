import os.path
import serial
import time
import platform
import glob
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional, Union, List


class ArduinoController:
    def __init__(
            self,
            com_port: str,
            baudrate: int = 115200,
            timeout: int = 5,
            system_ready_msg: str = "System ready",
            name: str = "ArduinoController"
    ) -> None:
        self.com_port = com_port
        self.baudrate = baudrate
        self.timeout = timeout
        self.system_ready_msg = system_ready_msg
        self.device: Optional[serial.Serial] = None
        self.name = name
        self.logger = self._setup_logger(name)
        self.plot, self.ax = plt.subplots()
        plt.ion()
        self.max_previous_plots = 10
        self.previous_plots: List[pd.DataFrame] = []

    @staticmethod
    def _setup_logger(name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        handler = RotatingFileHandler(f"{name}.log", maxBytes=10 * 1024 * 1024, backupCount=3)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    @staticmethod
    def list_serial_ports() -> List[str]:
        system_name = platform.system()
        if system_name == "Windows":
            return [f'COM{i}' for i in range(256) if ArduinoController._is_port_available(i)]
        elif system_name == "Darwin":
            return glob.glob('/dev/tty*') + glob.glob('/dev/cu*')
        else:
            return glob.glob('/dev/ttyS*') + glob.glob('/dev/ttyUSB*')

    @staticmethod
    def _is_port_available(port: int) -> bool:
        try:
            s = serial.Serial(port)
            s.close()
            return True
        except serial.SerialException:
            return False

    def connect(self) -> None:
        try:
            self.device = serial.Serial(self.com_port, self.baudrate, timeout=self.timeout)
            if not self.device.isOpen():
                self.device.open()
            time.sleep(1.2)
            self.device.reset_input_buffer()
            self.logger.info(
                f"Connected to device at {self.com_port} with baud rate {self.baudrate} and timeout {self.timeout}")
        except serial.SerialException as e:
            self.logger.error(f"Failed to connect to device at {self.com_port}: {e}")
            raise

    def disconnect(self) -> None:
        if self.device is not None:
            self.device.flush()
            self.device.close()
            self.device = None
            self.logger.info("Disconnected from device")

    def reconnect_after_reboot(self, attempts: int = 10, delay: int = 1) -> None:
        for attempt in range(attempts):
            try:
                self.connect()
                return
            except serial.SerialException as err:
                self.logger.info(f'Connection attempt {attempt + 1} failed with err={err}, retrying after delay...')
                time.sleep(delay)
        raise ConnectionError(f'Failed to reconnect to the Arduino device after {attempts} attempts.')

    def read_serial(self) -> Optional[str]:
        if self.device is None:
            return None
        response = self.device.readline().decode().strip()
        self.logger.debug(f"Message from {self.name}: {response}")
        return response

    def clear_serial(self) -> None:
        while self.device and self.device.in_waiting != 0:
            self.read_serial()

    def send_command(self, mode: str, value: int = 0) -> None:
        if self.device is None:
            self.logger.error("No device connected.")
            raise ConnectionError("No device connected.")
        message = f"{mode}{value}"
        self.device.write(message.encode())
        self.logger.debug(f"Sent: {message.strip()}")
        response = self.read_serial()
        self._handle_response(response)

    def _handle_response(self, response: Optional[str]) -> None:
        if response == '-1':
            self.logger.info("Command executed successfully.")
            print("Command executed successfully.")
        elif response == '-2':
            self.logger.error("Command execution failed.")
            raise ValueError("Command execution failed.")
        else:
            self.logger.error("Received unexpected response.")
            raise ConnectionError("Received unexpected response.")

    def send_command_and_wait(self, command: str, value: int = 0, wait_timeout: int = 600) -> None:
        self.send_command(command, value)
        start_time = time.time()
        while True:
            line = self.read_serial()
            if self.system_ready_msg in line:
                break
            else:
                self.logger.debug(line)
            if time.time() - start_time > wait_timeout:
                err_msg = f"Waited more than {wait_timeout} seconds for system ready message after sending command: {command}"
                self.logger.error(err_msg)
                raise TimeoutError(err_msg)

    def send_command_get_csv(self, command: str, value: int = 0) -> pd.DataFrame:
        self.send_command(command, value)
        data = {'timestamp': [], 'value': []}
        while True:
            line = self.device.readline().decode().strip()
            if line == self.system_ready_msg:
                break
            timestamp, value = line.split(",")
            data['timestamp'].append(float(timestamp))
            data['value'].append(float(value))
        return pd.DataFrame(data)

    def send_command_and_plot(self, command: str, value: int = 0, filename: Optional[str] = None) -> pd.DataFrame:
        df = self.send_command_get_csv(command, value)
        if not df.empty:
            self._plot_data(df)
            if filename:
                self._save_plot(df, filename)
        return df

    def _plot_data(self, df: pd.DataFrame) -> None:
        plt.figure(1)
        plt.ion()
        for i, old_df in enumerate(self.previous_plots):
            color = mcolors.CSS4_COLORS[f'lightblue{i % 10}']
            plt.plot(old_df['timestamp'], old_df['value'], color=color)
        plt.plot(df['timestamp'], df['value'], color='blue')
        plt.draw()
        plt.pause(0.001)
        self.previous_plots.append(df)
        if len(self.previous_plots) > self.max_previous_plots:
            self.previous_plots.pop(0)
        plt.show(block=False)

    def _save_plot(self, df: pd.DataFrame, filename: str) -> None:
        plt.savefig(filename)
        df.to_csv(os.path.splitext(filename)[0] + '.csv')

    def do_idle(self) -> None:
        self.logger.info('Entering idle mode')
        self.send_command_and_wait(command='i', value=1)

    def exit_idle(self) -> None:
        self.logger.info('Exiting idle mode')
        self.send_command_and_wait(command='i', value=0)
