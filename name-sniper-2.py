import requests
import json
import datetime
import time
from queue import Queue
from threading import Thread

# REPLACE the strings in this list with a list of the usernames you want to snipe
usernames = [
    'MINECRAFT',
    'NAME'
]

# REPLACE this with your bearer token
bearer_token = 'BEARER_TOKEN'

# How many attempts the sniper makes during a snipe (API is limited to 3-5 per second or something)
num_tries = 5

# How long (seconds) before the droptime that the sniper starts
offset = .5

# How long (seconds) the sniper will snipe for
length_of_snipe = .75

# Changes the call to view your profile rather than change your name (so it doesn't accidentally grab a test name)
testing = False

# API url, shouldn't need to touch this
api_url = 'https://api.minecraftservices.com/minecraft/profile'

# Code

# Worker for async calls
class Worker(Thread):
  """ Thread executing tasks from a given tasks queue """

  def __init__(self, tasks):
    Thread.__init__(self)
    self.tasks = tasks
    self.daemon = True
    self.start()

  def run(self):
    while True:
      func, args, kargs = self.tasks.get()
      try:
        func(*args, **kargs)
      except Exception as e:
        # An exception happened in this thread
        print(e)
      finally:
        # Mark this task as done, whether an exception happened or not
        self.tasks.task_done()

# Threads for async calls
class ThreadPool:
  """ Pool of threads consuming tasks from a queue """

  def __init__(self, num_threads):
    self.tasks = Queue(num_threads)
    for _ in range(num_threads):
      Worker(self.tasks)

  def add_task(self, func, *args, **kargs):
    """ Add a task to the queue """
    self.tasks.put((func, args, kargs))

  def map(self, func, args_list):
    """ Add a list of tasks to the queue """
    for args in args_list:
      self.add_task(func, args)

  def wait_completion(self):
    """ Wait for completion of all the tasks in the queue """
    self.tasks.join()

# Method for a a single attempt
def attempt_thread(attempt_data):
    time.sleep(attempt_data['attempt_num'] * length_of_snipe/num_tries)
    my_headers = {'Authorization' : 'Bearer ' + bearer_token}
    if testing:
        # GET current profile (for testing)
        response = requests.get(api_url, headers=my_headers)
    elif new_profile:
        # POST for a new profile
        response = requests.post(api_url, headers=my_headers, data={ "profileName" : attempt_data['name'] })
    else:
        # PUT for a new profile
        response = requests.put(api_url + "/name/" + attempt_data['name'], headers=my_headers)
    if (response.status_code == 200):
        print(attempt_data['name'] + ": Attempt " + str(attempt_data['attempt_num']+1) + " Succeeded!")
    else:
        print(attempt_data['name'] + ": Attempt " + str(attempt_data['attempt_num']+1) + " Failed: " + str(response.status_code))

# Check for token validity
print("Authenticating...")
print("")
my_headers = {'Authorization' : 'Bearer ' + bearer_token}
response = requests.get(api_url, headers=my_headers)
if (response.status_code == 200):
    print("Your current profile name is: " + response.json()['name'])
    new_profile = False
elif (response.status_code == 404):
    print("You haven't set up your profile.")
    new_profile = True
else:
    print("Authentication failed. Check your bearer token.")
    print("Would you like to continue anyways? (y or n)")
    auth_err = input(">")
    if auth_err != "y":
        exit()

print("")
print("Starting the Sniper. Press ctrl+C to stop the sniper at any time.")
print("")


# Get unix timecodes for the list of names
print("Finding the droptimes of the names...")
droptimes = {}
for username in usernames:
    response = requests.get("https://api.coolkidmacho.com/droptime/" + username)
    if (response.status_code == 200):
        droptime = response.json()['UNIX']
        droptimes[username] = droptime
        print("Droptime for " + username + " is: " + datetime.datetime.fromtimestamp(int(droptime)).strftime('%m/%d/%Y %H:%M:%S'))
    else:
        print("Looks like the name " + username + " won't be available any time soon.")
print(droptimes)

# Main loop
running = True
while running:
    current_time = time.time()
    for name in droptimes.keys():
        if current_time > droptimes[name] - offset:
            attempt_data_list = [{'name': name, 'attempt_num': i} for i in range(num_tries)]
            pool = ThreadPool(num_tries)

            r = requests.session()
            pool.map(attempt_thread, attempt_data_list)
            droptimes.pop(name, None)
            break
    time.sleep(.1)
