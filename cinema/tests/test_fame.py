from django.test import TestCase

import numpy as np
from numpy.linalg import norm

from cinema.cinegraph.grapher import PersonNode, WorkNode
from cinema.tests import data4tests
from cinema.cinegame import fame


class TestFame(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_normalized_exponential_decay(self):
        actual = fame.normalized_exponential_decay(4)
        expected = np.array([0.56285534, 0.26060938, 0.12066555, 0.05586973])
        self.assertAlmostEqual(0, norm(actual - expected))

    def test_get_people(self):
        g = data4tests.get_small_graph()
        people = fame.get_people(g)
        self.assertEqual(660, len(people))
        self.assertTrue(PersonNode(1669) in people)
        for p in people:
            self.assertTrue(p.is_person)

    def test_get_works(self):
        g = data4tests.get_small_graph()
        works = fame.get_works(g)
        self.assertEqual(300, len(works))
        self.assertTrue(WorkNode(119567) in works)
        for w in works:
            self.assertFalse(w.is_person)

    def test_fame_by_number_of_works(self):
        g = data4tests.get_small_graph()
        people_degree = fame.fame_by_number_of_works(g)
        self.assertEqual(660, len(people_degree))
        actual = [p for p, _ in people_degree[:4]]
        expected = [PersonNode(194), PersonNode(545), PersonNode(147), PersonNode(93)]
        self.assertEqual(expected, actual)
        actual = [d for _, d in people_degree[:4]]
        expected = [57, 56, 50, 46]
        self.assertEqual(expected, actual)

    def test_fame_by_pageranks(self):
        g = data4tests.get_small_graph()
        people_rank, _ = fame.fame_by_pagerank(g)
        actual = [p for p, _ in people_rank[:4]]
        expected = [PersonNode(545), PersonNode(194), PersonNode(147), PersonNode(93)]
        self.assertEqual(expected, actual)
        actual = [r for _, r in people_rank[:4]]
        expected = np.array(
            [
                0.02079940230132745,
                0.01956018860654516,
                0.01724945845804374,
                0.01593796482225136,
            ]
        )
        self.assertAlmostEqual(0, norm(actual - expected))

    def test_works_by_pagerank(self):
        g = data4tests.get_small_graph()
        works_rank, _ = fame.works_by_pagerank(g)
        actual = [w for w, _ in works_rank[:4]]
        expected = [
            WorkNode(3154822),
            WorkNode(118901),
            WorkNode(1233192),
            WorkNode(98638),
        ]
        self.assertEqual(expected, actual)
        actual = [r for _, r in works_rank[:4]]
        expected = np.array(
            [
                0.0033347298102977384,
                0.0019010827959628127,
                0.0019010827959628127,
                0.0019010827959628127,
            ]
        )
        self.assertAlmostEqual(0, norm(actual - expected))