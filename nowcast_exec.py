import time, os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

path = '/usr/iris_data/to_PYSTEPS'

class Watcher:
    DIRECTORY_TO_WATCH = path

    def __init__(self):
        self.observer = Observer()

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.DIRECTORY_TO_WATCH, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except:
            self.observer.stop()
            print("Error")

        self.observer.join()


class Handler(FileSystemEventHandler):

    @staticmethod
    def on_any_event(event):
        if event.is_directory:
            return None

        elif event.event_type == 'created':
            # Take any action here when a file is first created.
            print("Received created event - %s." % event.src_path)
            try:
                exec(open("LK_nowcast.py").read())
                exec(open("ensemble_nowcast.py").read())
            except:
                print('no valid data')
            # remove older data in path
            now = time.time()
            for filename in os.listdir(path):
                if os.path.getmtime(os.path.join(path, filename)) < now - 7 * 86400:
                    if os.path.isfile(os.path.join(path, filename)):
                        os.remove(os.path.join(path, filename))

if __name__ == '__main__':
    w = Watcher()
    w.run()
