import time

import concurrent


def square(a: float):
    return a**2

if __name__ == '__main__':
    
    resource = concurrent.WorkerResource(square)
    print(resource)
    print(resource.is_alive())
    resource.start()
    print(resource.is_alive())
    resource.terminate()
    print(resource.is_alive())
    
    with concurrent.WorkerResource(square) as w:
        print(w.execute(5))
        print(w.get_status())
        time.sleep(1)
        print(w.get_status())
        