import os
import unittest
from unittest.mock import patch
from core.optimization.mutant import Zoo, Mutant


class TestZoo(unittest.TestCase):
    def test_get_optimal_choice(self):
        choice_records = {
            'choice1': {'pulls': 10, 'rewards': 3},
            'choice2': {'pulls': 8, 'rewards': 5},
            'choice3': {'pulls': 15, 'rewards': 4}
        }
        with patch('random.betavariate', side_effect=[0.2, 0.5, 0.3]):
            best_choice = Zoo.get_optimal_choice(choice_records)
        self.assertEqual(best_choice, 'choice2')


class TestMutant(unittest.TestCase):
    def test_initialization(self):
        mutant = Mutant()
        self.assertEqual(mutant.age, 0)
        self.assertTrue(isinstance(mutant.properties, dict))
        self.assertGreaterEqual(len(mutant.properties), 1)

    def test_pull_and_reward(self):
        mutant = Mutant()
        initial_pulls = mutant.pulls
        initial_rewards = mutant.rewards
        mutant.pull()
        self.assertEqual(mutant.pulls, initial_pulls + 1)
        mutant.reward()
        self.assertEqual(mutant.rewards, initial_rewards + 1)


class TestMutantMethods(unittest.TestCase):
    def setUp(self):
        self.parent_mutant = Mutant(mutation_rate=0.1, mutation_strength=0.2)

    def test_spawn_child_mutation(self):
        with patch('random.random', side_effect=[0.05, 1, 1, 1, 1]), patch('random.choice', return_value=5):
            child = self.parent_mutant.spawn_child()
            # Assuming 'test_property_0' was selected for mutation
            self.assertEqual(child.properties['test_property_0'], 5)

    def test_crossover(self):
        other_mutant = Mutant()
        with patch('random.random', side_effect=[0.6] * len(Mutant.PROPERTIES)):
            child = self.parent_mutant.crossover(other_mutant)
            for prop in Mutant.PROPERTIES:
                self.assertEqual(child.properties[prop], other_mutant.properties[prop])

    def test_save_and_load(self):
        filename = './data/test_gallery/test_mutant.json'
        self.parent_mutant.save(filename)
        loaded_mutant = Mutant.load(filename)
        self.assertEqual(self.parent_mutant.properties, loaded_mutant.properties)
        self.assertEqual(self.parent_mutant.age, loaded_mutant.age)
        os.remove(filename)  # Cleanup after test

    def test_genetic_diversity(self):
        population = [Mutant() for _ in range(10)]
        diversity = Mutant.genetic_diversity(population)
        self.assertTrue(isinstance(diversity, float))
        self.assertGreaterEqual(diversity, 0)

    @patch('concurrent.futures.ThreadPoolExecutor.submit')
    @patch('concurrent.futures.wait')
    def test_parallel_evaluate(self, mock_wait, mock_submit):
        population = [Mutant() for _ in range(10)]
        fitness_functions = [lambda mutant: mutant.age]
        Mutant.parallel_evaluate(population, fitness_functions)
        mock_submit.assert_called()
        mock_wait.assert_called()

    def test_select_elites(self):
        population = [Mutant(age=i) for i in range(10)]
        Mutant.parallel_evaluate(population, [lambda mutant: mutant.age])
        elites = Mutant.select_elites(population, 2)
        self.assertEqual(len(elites), 2)
        self.assertEqual(elites[0].age, 9)
        self.assertEqual(elites[1].age, 8)

    def test_log_population(self):
        population = [Mutant(age=i) for i in range(3)]
        Mutant.parallel_evaluate(population, [lambda mutant: mutant.age])
        with patch('builtins.print') as mock_print:
            Mutant.log_population(population, 1)
            mock_print.assert_called()


# class TestOptimizerIntegration(unittest.TestCase):
#     def setUp(self):
#         self.optimizer = Optimizer()
#         self.zoo = Zoo()
#         self.mutants = [Mutant() for _ in range(5)]
#
#     @patch('your_module.Zoo.get_optimal_choice')
#     def test_optimizer_run(self, mock_get_optimal_choice):
#         # Setup mock return value to simulate optimal choice selection
#         mock_get_optimal_choice.return_value = 'mutant_optimal'
#
#         # Assuming 'run' method takes a list of mutants and selects the best one
#         # This is a simplification and would need to match your actual implementation
#         best_mutant = self.optimizer.run(self.zoo, self.mutants, some_test_func, some_eval_func)
#         self.assertEqual(best_mutant, 'mutant_optimal')


if __name__ == '__main__':
    unittest.main()
