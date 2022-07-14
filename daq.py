import nidaqmx
from nidaqmx.constants import TerminalConfiguration

i=0

#task = nidaqmx.Task()
#task.ai_channels.add_ai_voltage_chan("cDAQ1Mod1/ai0", terminal_config = TerminalConfiguration.RSE)
#data = task.read(number_of_samples_per_channel=1)
#print(data)
#task.close()
with nidaqmx.Task() as task:
    task.ai_channels.add_ai_voltage_chan("cDAQ1Mod1/ai0", terminal_config = TerminalConfiguration.RSE)

    while i<100:
        data = task.read(number_of_samples_per_channel=1)
        
#         plt.scatter(i,data[0],c="r")
#         plt.pause(0.05)
        print(data)
        
        i=i+1