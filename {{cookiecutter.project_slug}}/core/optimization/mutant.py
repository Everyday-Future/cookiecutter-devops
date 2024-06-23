import random
import json
import copy
import statistics
import concurrent.futures


class Optimizer:
    """
    Manage experiments to accumulate pulls and rewards until the best strategy is discovered.
    """

    def run(self, zoo, test_func, eval_func):
        pass


class Zoo:
    """
    Collection of Mutants to be sampled from with a multi-armed bandit based on their reward rate.
    """

    @staticmethod
    def get_optimal_choice(choice_records: dict):
        """
        Get the best choice from a dict of {choice_name: {'pulls': 0, 'rewards': 0}, ...} using thompson sampling
        :param choice_records:
        :type choice_records:
        :return:
        :rtype:
        """
        sampled_theta = {}
        for key, choice in choice_records.items():
            # Draw from beta distribution of beta( prior[0] + trials, prior[1] + failures )
            pulls, rewards = float(choice['pulls']), float(choice['rewards'])
            dist = random.betavariate(1.0 + rewards, 1.0 + pulls - rewards)
            sampled_theta[key] = dist
        return max(sampled_theta, key=sampled_theta.get)


class Mutant:
    """
    Represents a mutant in a genetic algorithm, with properties, mutation rate, mutation strength,
    and support for multi-objective optimization and elitism.

    PROPERTIES should be overridden by the child class. These are the "genome" of the class
    and instances sample from it.

    Attributes:
        mutation_rate (float): The probability of a property mutating when spawning a child mutant.
        mutation_strength (float): The maximum percentage change allowed in a property value during mutation.
        age (int): The age of the mutant in generations.
        history (list): A list of historical records of the mutant's properties.
        mutation_history (list): A list of historical records of mutations.
        fitness (list): The fitness values of the mutant for each objective in multi-objective optimization.
    """
    PROPERTIES = {
        'test_property_0': list(range(10)),
        'test_property_1': ['single', 'double', 'triple'],
        'test_property_2': list(range(10)),
        'test_property_3': list(range(10)),
        'test_property_4': list(range(10))
    }

    def __init__(self, properties=None, mutation_rate=0.1, mutation_strength=0.2, age=0, history=None,
                 mutation_history=None, **kwargs):
        """
        Initializes a new instance of the Mutant class.

        :param mutation_rate: The probability of a property mutating when spawning a child mutant, defaults to 0.1.
        :type mutation_rate: float, optional
        :param mutation_strength: The maximum percentage change in a property value during mutation, default==0.2.
        :type mutation_strength: float, optional
        :param age: The age of the mutant in generations, defaults to 0.
        :type age: int, optional
        :param history: A list of historical records of the mutant's properties, defaults to None.
        :type history: list, optional
        :param mutation_history: A list of historical records of mutations, defaults to None.
        :type mutation_history: list, optional
        """
        self.mutation_rate = mutation_rate
        self.mutation_strength = mutation_strength
        self.age = age
        self.history = history if history is not None else []
        self.mutation_history = mutation_history if mutation_history is not None else []
        self.properties = {}
        if properties is not None:
            self.properties = copy.deepcopy(properties)
        else:
            for prop, value_range in self.PROPERTIES.items():
                self.properties[prop] = random.choice(value_range)
        self.log_history()
        self._fitness = None
        self.pulls = kwargs.get('pulls', 0)
        self.rewards = kwargs.get('rewards', 0)

    def pull(self):
        self.pulls += 1

    def reward(self):
        self.rewards += 1

    def spawn_child(self):
        """
        Spawns a child mutant with properties potentially mutated based on the mutation rate and strength.

        :return: A new instance of the Mutant class representing the child mutant.
        :rtype: Mutant
        """
        child_properties = {}
        child_mutation_history = []
        for prop, value in self.properties.items():
            if random.random() < self.mutation_rate:
                # Mutate the property within the bounds of mutation strength
                mutation = random.choice(self.PROPERTIES[prop])
                child_properties[prop] = mutation
                child_mutation_history.append({prop: mutation})
            else:
                # Inherit the property from the parent
                child_properties[prop] = value
        child_mutant = Mutant(properties=child_properties,
                              mutation_rate=self.mutation_rate,
                              mutation_strength=self.mutation_strength,
                              age=self.age + 1,
                              history=child_mutation_history + copy.deepcopy(self.history))
        return child_mutant

    def crossover(self, other):
        """
        Performs crossover between this mutant and another mutant to produce a child mutant.

        :param other: Another mutant to crossover with.
        :type other: Mutant
        :return: A new instance of the Mutant class representing the child mutant.
        :rtype: Mutant
        """
        child_properties = {}
        for prop in self.properties:
            if random.random() < 0.5:
                child_properties[prop] = self.properties[prop]
            else:
                child_properties[prop] = other.properties[prop]
        return Mutant(properties=child_properties,
                      mutation_rate=self.mutation_rate,
                      mutation_strength=self.mutation_strength,
                      age=max(self.age, other.age) + 1,
                      history=copy.deepcopy(self.history))

    def log_history(self):
        """
        Logs the current properties and mutations of the mutant to the history.
        """
        self.history.append(copy.deepcopy(self.properties))
        self.mutation_history.append({'age': self.age, 'mutations': copy.deepcopy(self.mutation_history)})

    @staticmethod
    def genetic_diversity(population):
        """
        Calculates the genetic diversity of a population of mutants.

        :param population: A list of mutant instances.
        :type population: list
        :return: A measure of genetic diversity.
        :rtype: float
        """
        diversity = 0
        for prop in population[0].properties:
            values = [mutant.properties[prop] if isinstance(mutant.properties[prop], (int, float))
                      else hash(mutant.properties[prop])
                      for mutant in population]
            diversity += statistics.variance(values)
        return diversity

    def save(self, filename):
        """
        Saves the mutant to a file.

        :param filename: The name of the file to save the mutant to.
        :type filename: str
        """
        with open(filename, 'w') as file:
            json.dump({'properties': self.properties, 'mutation_rate': self.mutation_rate,
                       'mutation_strength': self.mutation_strength, 'age': self.age, 'history': self.history,
                       'mutation_history': self.mutation_history, 'fitness': self._fitness}, file)

    @staticmethod
    def load(filename):
        """
        Loads a mutant from a file.

        :param filename: The name of the file to load the mutant from.
        :type filename: str
        :return: A new instance of the Mutant class loaded from the file.
        :rtype: Mutant
        """
        with open(filename, 'r') as file:
            data = json.load(file)
        return Mutant(mutation_rate=data['mutation_rate'], mutation_strength=data['mutation_strength'], age=data['age'],
                      history=data['history'], mutation_history=data['mutation_history'],
                      properties=data['properties'])

    def __repr__(self):
        """
        Returns a string representation of the mutant, showing its properties and values.

        :return: A string representation of the mutant.
        :rtype: str
        """
        return (f'Mutant({self.properties}, mutation_rate={self.mutation_rate}, '
                f'mutation_strength={self.mutation_strength}, age={self.age}, fitness={self.fitness})')

    @staticmethod
    def evaluate_fitness(mutant, fitness_functions):
        """
        Evaluates the fitness of a mutant based on the provided fitness functions.

        :param mutant: The mutant to evaluate.
        :type mutant: Mutant
        :param fitness_functions: A list of fitness functions to evaluate the mutant.
        :type fitness_functions: list
        """
        mutant.fitness = [f(mutant) for f in fitness_functions]

    @staticmethod
    def parallel_evaluate(population, fitness_functions):
        """
        Evaluates the fitness of a population of mutants in parallel using the provided fitness functions.

        :param population: A list of mutants to evaluate.
        :type population: list
        :param fitness_functions: A list of fitness functions to evaluate the mutants.
        :type fitness_functions: list
        """
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(Mutant.evaluate_fitness, mutant, fitness_functions) for mutant in population]
            concurrent.futures.wait(futures)

    @staticmethod
    def select_elites(population, num_elites):
        """
        Selects the top-performing mutants from the population based on their fitness.

        :param population: A list of mutants to select from.
        :type population: list
        :param num_elites: The number of elite mutants to select.
        :type num_elites: int
        :return: A list of the selected elite mutants.
        :rtype: list
        """
        sorted_population = sorted(population, key=lambda x: x.fitness, reverse=True)
        return sorted_population[:num_elites]

    @staticmethod
    def log_population(population, generation):
        """
        Logs the properties and fitness of the population for a given generation.

        :param population: The population to log.
        :type population: list
        :param generation: The generation number.
        :type generation: int
        """
        print(f'Generation {generation}:')
        for mutant in population:
            print(f'  Mutant: {mutant}, Fitness: {mutant.fitness}')
