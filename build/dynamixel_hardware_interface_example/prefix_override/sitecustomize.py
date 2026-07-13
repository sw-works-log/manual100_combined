import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/sw/manual_total _ws/install/dynamixel_hardware_interface_example'
