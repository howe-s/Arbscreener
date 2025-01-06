import time

def runTime(func):
    def wrapper(*args, **kwargs):
        timeOne = time.time()
        result = func(*args, **kwargs)
        timeTwo = time.time() - timeOne
        print(f'{func.__name__} ran in {timeTwo} seconds')
        return result
    return wrapper
