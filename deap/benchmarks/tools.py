"""Module containing tools that are useful when benchmarking algorithms
"""
from math import sqrt
from functools import wraps
from itertools import repeat
try:
    import numpy
except ImportError:
    numpy = False

class translate(object):
    """Decorator for evaluation functions, it translates the objective
    function by *vector* which should be the same length as the individual
    size. When called the decorated function should take as first argument the
    individual to be evaluated. The inverse translation vector is actually
    applied to the individual and the resulting list is given to the
    evaluation function. Thus, the evaluation function shall not be expecting
    an individual as it will receive a plain list.
    
    This decorator adds a :func:`translate` function to the decorated
    function.
    """
    def __init__(self, vector):
        self.vector = vector
    
    def __call__(self, func):
        # wraps is used to combine stacked decorators that would add functions
        @wraps(func)
        def wrapper(individual, *args, **kargs):
            # A subtraction is applied since the translation is applied to the
            # individual and not the function
            return func([v - t for v, t in zip(individual, self.vector)], 
                *args, **kargs)
        wrapper.translate = self.translate
        return wrapper
    
    def translate(self, vector):
        """Set the current translation to *vector*. After decorating the
        evaluation function, this function will be available directly from
        the function object. ::
            
            @translate([0.25, 0.5, ..., 0.1])
            def evaluate(individual):
                return sum(individual),
            
            # This will cancel the translation
            evaluate.translate([0.0, 0.0, ..., 0.0])
        """
        self.vector = vector

class rotate(object):
    """Decorator for evaluation functions, it rotates the objective function
    by *matrix* which should be a valid orthogonal NxN rotation matrix, with N
    the length of an individual. When called the decorated function should
    take as first argument the individual to be evaluated. The inverse
    rotation matrix is actually applied to the individual and the resulting
    list is given to the evaluation function. Thus, the evaluation function
    shall not be expecting an individual as it will receive a plain list
    (numpy.array). The multiplication is done using numpy.
    
    This decorator adds a :func:`rotate` function to the decorated
    function.
    
    .. note::
    
       A random orthogonal matrix Q can be created via QR decomposition. ::
           
           A = numpy.random.random((n,n))
           Q, _ = numpy.linalg.qr(A)
    """
    def __init__(self, matrix):
        if not numpy:
            raise RuntimeError("Numpy is required for using the rotation "
                "decorator")
        # The inverse is taken since the rotation is applied to the individual
        # and not the function which is the inverse
        self.matrix = numpy.linalg.inv(matrix)

    def __call__(self, func):
        # wraps is used to combine stacked decorators that would add functions
        @wraps(func)
        def wrapper(individual, *args, **kargs):
            return func(numpy.dot(self.matrix, individual), *args, **kargs)
        wrapper.rotate = self.rotate
        return wrapper

    def rotate(self, matrix):
        """Set the current rotation to *matrix*. After decorating the
        evaluation function, this function will be available directly from
        the function object. ::
            
            # Create a random orthogonal matrix
            A = numpy.random.random((n,n))
            Q, _ = numpy.linalg.qr(A)
            
            @rotate(Q)
            def evaluate(individual):
                return sum(individual),
            
            # This will reset rotation to identity
            evaluate.rotate(numpy.identity(n))
        """
        self.matrix = numpy.linalg.inv(matrix)

class noise(object):
    """Decorator for evaluation functions, it evaluates the objective function
    and adds noise by calling the function(s) provided in the *noise*
    argument. The noise functions are called without any argument, consider
    using the :class:`~deap.base.Toolbox` or Python's
    :func:`functools.partial` to provide any required argument. If a single
    function is provided it is applied to all objectives of the evaluation
    function. If a list of noise functions is provided, it must be of length
    equal to the number of objectives. The noise argument also accept
    :obj:`None`, which will leave the objective without noise.

    This decorator adds a :func:`noise` function to the decorated
    function.
    """
    def __init__(self, noise):
        try:
            self.rand_funcs = tuple(noise)
        except TypeError:
            self.rand_funcs = repeat(noise)

    def __call__(self, func):
        # wraps is used to combine stacked decorators that would add functions
        @wraps(func)
        def wrapper(individual, *args, **kargs):
            result = func(individual, *args, **kargs)
            noisy = list()
            for r, f in zip(result, self.rand_funcs):
                if f is None:
                    noisy.append(r)
                else:
                    noisy.append(r + f())
            return tuple(noisy)
        wrapper.noise = self.noise
        return wrapper
    
    def noise(self, noise):
        """Set the current noise to *noise*. After decorating the
        evaluation function, this function will be available directly from
        the function object. ::
        
            prand = functools.partial(random.gauss, mu=0.0, sigma=1.0)
        
            @noise(prand)
            def evaluate(individual):
                return sum(individual),
        
            # This will remove noise from the evaluation function
            evaluate.noise(None)
        """
        try:
            self.rand_funcs = tuple(noise)
        except TypeError:
            self.rand_funcs = repeat(noise)
            
class scale(object):
    """Decorator for evaluation functions, it scales the objective function by
    *factor* which should be the same length as the individual size. When
    called the decorated function should take as first argument the individual
    to be evaluated. The inverse factor vector is actually applied to the
    individual and the resulting list is given to the evaluation function.
    Thus, the evaluation function shall not be expecting an individual as it
    will receive a plain list.
    
    This decorator adds a :func:`scale` function to the decorated
    function.
    """
    def __init__(self, factor):
        # Factor is inverted since it is aplied to the individual and not the
        # objective function
        self.factor = tuple(1.0/f for f in factor)

    def __call__(self, func):
        # wraps is used to combine stacked decorators that would add functions
        @wraps(func)
        def wrapper(individual, *args, **kargs):
            return func([v * f for v, f in zip(individual, self.factor)], 
                *args, **kargs)
        wrapper.scale = self.scale
        return wrapper

    def scale(self, factor):
        """Set the current scale to *factor*. After decorating the
        evaluation function, this function will be available directly from
        the function object. ::
            
            @scale([0.25, 2.0, ..., 0.1])
            def evaluate(individual):
                return sum(individual),
            
            # This will cancel the scaling
            evaluate.scale([1.0, 1.0, ..., 1.0])
        """
        # Factor is inverted since it is aplied to the individual and not the
        # objective function
        self.factor = tuple(1.0/f for f in factor)
        
def diversity(first_front, first, last):
    """Given a Pareto front `first_front` and two extreme point of the 
    optimal Pareto front, this function return a metric of the diversity 
    of the front as explained in the original NSGA-II article by K. Deb.
    The smaller is the value, the better is the front.
    """
    n = len(first_front)

    df = sqrt((first_front[0].fitness.values[0] - first[0])**2 +
              (first_front[0].fitness.values[1] - first[1])**2)
    dl = sqrt((first_front[-1].fitness.values[0] - last[0])**2 +
              (first_front[-1].fitness.values[1] - last[1])**2)
    d = [0.0] * (n-1)
    for i in xrange(len(d)):
       d[i] = sqrt((first_front[i].fitness.values[0] - first_front[i+1].fitness.values[0])**2 +
                   (first_front[i].fitness.values[1] - first_front[i+1].fitness.values[1])**2)
    dm = sum(d)/len(d)
    di = sum(abs(d_i - dm) for d_i in d)
    delta = (df + dl + di)/(df + dl + len(d) * dm )
    return delta

def convergence(first_front, optimal_front):
    """Given a Pareto front `first_front` and the optimal Pareto front, 
    this function return a metric of convergence
    of the front as explained in the original NSGA-II article by K. Deb.
    The smaller is the value, the closer the front is to the optimal one.
    """
    distances = []
    
    for ind in first_front:
        distances.append(float("inf"))
        for opt_ind in optimal_front:
            dist = 0.
            for i in xrange(len(opt_ind)):
                dist += (ind.fitness.values[i] - opt_ind[i])**2
            if dist < distances[-1]:
                distances[-1] = dist
        distances[-1] = sqrt(distances[-1])
        
    return sum(distances) / len(distances)