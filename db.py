import os
from supabase import create_client, Client

url = 'https://dfdnzxmtohnlzrtyigcw.supabase.co' 
key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRmZG56eG10b2hubHpydHlpZ2N3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mjk2NTIzNzUsImV4cCI6MjA0NTIyODM3NX0.1J0HBm00c76dWTrJZP-q34d24ToB5uq1i1BYtvbBPak'
supabase: Client = create_client(url, key)

# creates a preset in the database
def upload_preset(preset_name, id_lst, pname_lst, ymin_lst, ymax_lst):
  supabase.table("presets").insert({
  "preset_name": preset_name,
  "id": id_lst,
  "param_name": pname_lst,
  "y_min": ymin_lst,
  "y_max": ymax_lst
}).execute()

# returns a list of existing presets in the database
def get_preset_names():
  names = supabase.table("presets").select("preset_name").execute().data
  values_list = [item['preset_name'] for item in names]
  return values_list

# returns data of requested preset
def get_preset_info(preset_name):
  preset_info = supabase.table("presets").select().eq("preset_name", preset_name).execute().data
  return preset_info





