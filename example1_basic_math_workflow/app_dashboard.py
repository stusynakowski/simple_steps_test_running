
# load a table 

# perform a set of basic mathematical operations


# given an example that is requires some asyncronious processing

# write to a file

# move on


def create_list()->list[int]:
    return [1, 2, 3, 4, 5]


def sum(a:int|float, b:int|float=0)->int|float:
    return a + b


def multiply(a:int|float, b:int|float=1)->int|float:
    return a * b

def slow_multiply(a:int|float, b:int|float=1)->int|float:
    import time
    time.sleep(2)
    return a * b

#
    
