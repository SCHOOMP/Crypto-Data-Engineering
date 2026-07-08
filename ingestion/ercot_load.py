## Sample Ingestion ##
import gridstatus
iso = gridstatus.Ercot()
load = iso.get_load("today")        # DataFrame: Time, Load
fuel = iso.get_fuel_mix("today")  # DataFrame: Time, Wind, Solar,# ...
print(fuel)