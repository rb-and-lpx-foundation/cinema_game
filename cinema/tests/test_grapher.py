import networkx as nx
from cinema.cinegraph import grapher
from cinema.cinegraph.grapher import ProfessionalNode, PersonNode, WorkNode

from django.test import TestCase


class TestGrapher(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_professional_node(self):
        n0 = ProfessionalNode(42, 'movie')
        n1 = ProfessionalNode(42, 'movie')
        n2 = ProfessionalNode(41, 'movie')
        n3 = ProfessionalNode(42, 'person')

        self.assertEqual(n0, n1)
        self.assertEqual(hash(n0), hash(n1))

        self.assertNotEqual(n0, n2)
        self.assertNotEqual(hash(n0), hash(n2))

        self.assertNotEqual(n0, n3)
        self.assertNotEqual(hash(n0), hash(n3))

    def test_person_node(self):
        n0 = ProfessionalNode(42, 'person')
        n1 = PersonNode(42)

        self.assertEqual('person', n1.t)
        self.assertEqual(n0, n1)
        self.assertEqual(hash(n0), hash(n1))

    def test_movie_node(self):
        n0 = ProfessionalNode(42, 'work')
        n1 = WorkNode(42)

        self.assertEqual('work', n1.t)
        self.assertEqual(n0, n1)
        self.assertEqual(hash(n0), hash(n1))

    def test_add_arc(self):
        g = nx.Graph()
        grapher.add_arc(g, "The Air I Breathe", "Kevin Bacon", job="actor")
        grapher.add_arc(g, "The Air I Breathe", "Sarah Michelle Geller", job="actress")
        grapher.add_arc(g, "A Powerful Noise Live", "Sarah Michelle Geller", job="self")
        grapher.add_arc(g, "A Powerful Noise Live", "Natalie Portman", job="self")

        self.assertEqual(5, g.number_of_nodes())
        self.assertEqual(4, g.number_of_edges())

        self.assertIn(WorkNode("The Air I Breathe"), g.nodes)
        self.assertIn(WorkNode("A Powerful Noise Live"), g.nodes)

        self.assertIn(PersonNode("Kevin Bacon"), g.nodes)
        self.assertIn(PersonNode("Sarah Michelle Geller"), g.nodes)
        self.assertIn(PersonNode("Natalie Portman"), g.nodes)

        self.assertEqual(
            {"actor"},
            g.edges[(WorkNode("The Air I Breathe"), PersonNode("Kevin Bacon"))]["job"],
        )
        self.assertEqual(
            {"actress"},
            g.edges[
                (WorkNode("The Air I Breathe"), PersonNode("Sarah Michelle Geller"))
            ]["job"],
        )
        self.assertEqual(
            {"self"},
            g.edges[
                (
                    WorkNode("A Powerful Noise Live"),
                    PersonNode("Sarah Michelle Geller"),
                )
            ]["job"],
        )
        self.assertEqual(
            {"self"},
            g.edges[
                (WorkNode("A Powerful Noise Live"), PersonNode("Natalie Portman"))
            ]["job"],
        )

    def test_professional_node_in_graph(self):
        # IMDB ids are integers. There are movies and people which have the same id.
        # We need node objects which can be either movies or people and which are distinct even having the same
        # integer id.

        g = nx.Graph()
        n0 = ProfessionalNode(42, "person")
        n1 = ProfessionalNode(42, "movie")
        n2 = ProfessionalNode(48, "movie")

        m0 = ProfessionalNode(42, "person")
        m1 = ProfessionalNode(42, "movie")
        m2 = ProfessionalNode(48, "movie")
        m3 = ProfessionalNode(0, "person")

        g.add_node(n0)
        g.add_node(n1)
        g.add_node(n2)

        self.assertIn(n0, g.nodes)
        self.assertIn(n1, g.nodes)
        self.assertIn(n2, g.nodes)

        self.assertIn(m0, g.nodes)
        self.assertIn(m1, g.nodes)
        self.assertIn(m2, g.nodes)
        self.assertNotIn(m3, g.nodes)
