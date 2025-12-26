import unittest

from arc_export import Bookmark, Folder, parse_arc_sidebar, render_bookmarks_html


def synthetic_sidebar_data():
    return {
        "root": {
            "sidebar": {
                "containers": [
                    {
                        "items": [
                            {
                                "id": "space_root",
                                "title": "Space One",
                                "data": {"itemContainer": {}},
                                "parentID": None,
                            },
                            {
                                "id": "list1",
                                "title": "Reading",
                                "data": {"list": {}},
                                "parentID": "space_root",
                            },
                            {
                                "id": "tab1",
                                "data": {
                                    "tab": {
                                        "savedURL": "https://example.com",
                                        "savedTitle": "Example",
                                    }
                                },
                                "parentID": "list1",
                            },
                            {
                                "id": "tab2",
                                "data": {
                                    "tab": {
                                        "savedURL": "https://example.org",
                                        "savedTitle": "Example Org",
                                    }
                                },
                                "parentID": "list1",
                            },
                        ]
                    }
                ]
            }
        }
    }


class ArcExportTests(unittest.TestCase):
    def test_parse_tree(self):
        nodes, stats = parse_arc_sidebar(synthetic_sidebar_data())
        self.assertEqual(stats.tabs, 2)
        self.assertEqual(len(nodes), 1)

        root = nodes[0]
        self.assertIsInstance(root, Folder)
        self.assertEqual(root.title, "Arc Export (Container 1)")
        self.assertEqual(len(root.children), 1)

        space = root.children[0]
        self.assertIsInstance(space, Folder)
        self.assertEqual(space.title, "Space One")
        self.assertEqual(len(space.children), 1)

        reading = space.children[0]
        self.assertIsInstance(reading, Folder)
        self.assertEqual(reading.title, "Reading")
        self.assertEqual(len(reading.children), 2)

        self.assertIsInstance(reading.children[0], Bookmark)
        self.assertEqual(reading.children[0].url, "https://example.com")
        self.assertIsInstance(reading.children[1], Bookmark)
        self.assertEqual(reading.children[1].url, "https://example.org")

    def test_html_writer(self):
        nodes, _ = parse_arc_sidebar(synthetic_sidebar_data())
        html_output = render_bookmarks_html(nodes)
        self.assertIn("<H3>Arc Export (Container 1)</H3>", html_output)
        self.assertIn("<H3>Space One</H3>", html_output)
        self.assertIn("<H3>Reading</H3>", html_output)
        self.assertIn(
            '<A HREF="https://example.com">Example</A>', html_output
        )
        self.assertIn(
            '<A HREF="https://example.org">Example Org</A>', html_output
        )


if __name__ == "__main__":
    unittest.main()
