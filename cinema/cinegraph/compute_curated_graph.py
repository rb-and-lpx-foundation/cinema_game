import pandas as pd
import networkx as nx
from cinema.cinegraph.node_types import PersonNode, WorkNode
from cinema.cinegame.game_maker import GameMaker


class Curator:
    def __init__(self, g, ia, actor_names, movie_titles):
        self.g = g
        self.ia = ia
        self.actor_names = actor_names
        self.movie_titles = movie_titles
        self.actors = {name: self.actor_lookup(name) for name in actor_names}
        self.movies = {title: self.movie_lookup(title) for title in movie_titles}
        self.actor_by_id = {
            int(self.actors[name].getID()): name for name in self.actor_names
        }
        self.movie_by_id = {
            int(self.movies[title].getID()): title for title in self.movie_titles
        }
        self.curated_graph = self.make_curated_graph()
        self.game_maker = GameMaker(self.curated_graph)

    def movie_lookup(self, title):
        movies = self.ia.search_movie(title)
        if not len(movies):
            raise ValueError("No movie found with title: {}".format(title))
        return movies[0]

    def actor_lookup(self, name):
        actors = self.ia.search_person(name)
        if not len(actors):
            raise ValueError("No actor found with name: {}".format(name))
        return actors[0]

    def make_movie_df(self):
        ids = pd.Series(
            [self.movies[title].getID() for title in self.movie_titles], dtype=str
        )
        years = [
            self.movies[title].data.get("year", None) for title in self.movie_titles
        ]
        return pd.DataFrame({"IMDb_ID": ids, "year": years, "title": self.movie_titles})

    def make_actor_df(self):
        ids = pd.Series(
            [self.actors[name].getID() for name in self.actor_names], dtype=str
        )
        return pd.DataFrame({"IMDb_ID": ids, "name": self.actor_names})

    def make_curated_graph(self):
        actor_ids = [self.actors[name].getID() for name in self.actor_names]
        movie_ids = [self.movies[title].getID() for title in self.movie_titles]
        actor_nodes = [PersonNode(int(i)) for i in actor_ids]
        movie_nodes = [WorkNode(int(i)) for i in movie_ids]

        return self.g.subgraph(actor_nodes + movie_nodes)

    def plot_path(self, a, b):
        def lookup(n):
            if n.is_person:
                return self.actor_by_id[n.id]
            else:
                return self.movie_by_id[n.id]

        path = nx.shortest_path(self.curated_graph, a, b)

        return [lookup(n) for n in path]
