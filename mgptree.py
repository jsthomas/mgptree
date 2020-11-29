"""A CLI tool for scraping the mathematics genealogy project and generating family trees."""

import logging
import argparse
import re
import sys
import pickle
import textwrap
from typing import Tuple, List, Optional

import requests
import urllib3

# Note: The MGP site appears to have a problem with its certificate that triggers SSL exceptions in requests.
# Since security/privacy is not, in the author's opinion, a significant concern for this application,
# SSL warnings will be suppressed and the requests library will be configured to skip certificate validation.

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(message)s",
                    datefmt="%m/%d/%Y %I:%M:%S %p")
logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

GRAPH_FORMAT_STRING = "digraph G{\n node[width = 0.5 fontname=Courier shape=rectangle]\n %s}"


def build_opt_parser():
    """Construct a CLI option parser for the application."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--scrape", "-s", dest="scrape_on", action="store_true",
                        default=False, help="Recover data from the MGP.")
    parser.add_argument("--plot", "-p", dest="graph_on", action="store_true",
                        default=False, help="Use graphviz to draw a genealogy.")
    parser.add_argument("--generations", "-g", dest="gen_depth", default=3,
                        help="Determines how many generations into the past to search/print.")
    parser.add_argument("--input", "-i", dest="input_file", default=None)
    parser.add_argument("--output", "-o", dest="output_file", default=None)

    return parser


def main():  # pylint: disable=missing-docstring
    parser = build_opt_parser()
    args = parser.parse_args()

    if args.scrape_on:
        names = validate_scrape(parser, args)
        nodes = scrape(names, int(args.gen_depth))
        pickle_graph_ds(nodes, args.output_file)

    elif args.graph_on:
        nodes = validate_graph(parser, args)
        nodes_txt = graph(nodes, int(args.gen_depth))
        write_graph_text(nodes_txt, args.output_file)

    else:
        sys.stderr.write("Error: You must select either -s or -p.\n")
        parser.print_help()
        sys.exit(1)

    sys.exit(0)


def validate_scrape(parser, options):
    """Consume and validate user input options for scraping."""
    if options.input_file is None:
        sys.stderr.write("You must provide as input a file of names "
                         + "you wish to search for in the MGP.\n")
        parser.print_help()
        sys.exit(1)
    try:
        namefile = open(options.input_file, "rb")
    except IOError:
        sys.stderr.write("Error: Input file %s does not exist.\n" % options.names_file)
        parser.print_help()
        sys.exit(1)

    text = namefile.read().decode("utf8")
    names = [parse_name(line) for line in text.split("\n") if len(line) > 0]
    namefile.close()

    return names


def parse_name(name_line: str) -> Tuple[str, str, str]:
    """Normalize a name string to a name tuple."""

    if "," in name_line:
        comma = name_line.index(",")
        last = (name_line[0:comma]).strip().lower()
        name_line = (name_line[comma:]).replace(",", "")
        names = [last] + [name.strip().lower() for name in name_line.split()]

    else:
        name_line = name_line.replace(",", "")
        names = [name.strip().lower() for name in name_line.split()]

    if len(names) == 2:
        return names[0], names[1], ""
    if len(names) >= 3:
        return names[0], names[1], names[2]
    else:
        sys.stderr.write(("Error: Only detected a single name in string %s. " +
                          "Please provide a first and last name.\n") % name_line)
        sys.exit(1)


def scrape(names: List[Tuple[str, str, str]], gens: int) -> dict:
    """Scrape N generations of records from the MGP website.

    Arguments:
    names - A list of name tuples.
    gens - An integer number of generations to search back from the initial names.

    Returns:
    A dictionary mapping MGP primary keys to node objects.
    """
    node_dict = {}

    for name in names:
        mgp_id = fetch_id_num(*name)
        if mgp_id is None:
            continue
        Node(mgp_id, 0, gens, node_dict)

    return node_dict


def pickle_graph_ds(nodes: dict, filename: str):
    """Persist a dictionary of tree nodes to disk."""
    if filename is None:
        filename = "database.mgp"
    pickle.dump(nodes, open(filename, "wb"))
    sys.stdout.write("Saved %d records to file %s.\n" % (len(nodes), filename))


def validate_graph(parser, options) -> dict:
    """Consume and validate user input options for graphing."""
    if options.input_file is None:
        sys.stderr.write("Error: You must provide a saved database as input.\n")
        parser.print_help()
        sys.exit(1)

    try:
        nodes = pickle.load(open(options.input_file, "rb"))
    except IOError:
        sys.stderr.write("Error: Could not read file %s.", options.input_file)
        parser.print_help()
        sys.exit(1)

    return nodes


def graph(nodes, gen_depth):
    """Emit dot code for nodes below a certain generation."""
    node_strings = set()
    for _, node in nodes.items():
        if node.gen <= gen_depth:
            node_strings.add(node.dot_string(node.gen != gen_depth))
    return "".join(node_strings)


def write_graph_text(node_text, filename):
    """Emit a complete dotfile to disk or stdout."""

    fulltext = GRAPH_FORMAT_STRING % node_text
    if filename is None:
        sys.stdout.write(fulltext)
    else:
        outfile = open(filename, "wb")
        outfile.write(fulltext.encode("utf8"))
        outfile.close()


def same_name(name1: Tuple[str, str, str], name2: Tuple[str, str, str]):
    """Test if two name tuples are equivalent."""
    last1 = name1[0].lower()
    last2 = name2[0].lower()
    first1 = name1[1].lower()
    first2 = name2[1].lower()
    return last1 == last2 and first1 == first2


def fetch_id_num(last: str, first: str, middle: str) -> Optional[int]:
    """Attempt to determine the MGP primary key for the input name."""
    logger.info("Searching MGP for primary key. last=%s, first=%s, middle=%s", last, first, middle)

    url = "https://genealogy.math.ndsu.nodak.edu/query-prep.php"
    values = {
        "given_name": first,
        "family_name": last,
        "other_names": middle
    }

    text = (requests.post(url, values, verify=False)).text

    matches = re.findall(r'<tr><td><a href="id.php\?id=(\d+)">(.+)</a></td>', text)
    pairs = [(int(pair[0]), parse_name(pair[1])) for pair in matches]
    ids = [p[0] for p in pairs if same_name(p[1], (last, first, middle))]

    if not ids:
        logger.error("Unable to find a ID for name. last=%s, first=%s middle=%s",
                     last, first, middle)
        return None

    if len(ids) > 1:
        logger.error("Found multiple IDs for name. last=%s, first=%s middle=%s",
                     last, first, middle)
        return None

    logging.info("Found ID for name. last=%s, first=%s, middle=%s, id=%d",
                 last, first, middle, ids[0])
    return ids[0]


class Node:
    """Nodes record all data collected on a particular mathematician.

    Typically this information comes from entries in the
    Mathematics Genealogy project, and thus will not be complete.

    The most important piece of data the Node class manages is the
    (unique) ID number assigned to each mathematician by the MGP. This
    integer provides the best way to search for a given mathematician,
    since mapping names to people can be quite difficult.
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, id_number: int, gen: int, max_gen: int, node_data: dict):
        node_data[id_number] = self
        self.id_num = id_number
        self.gen = gen

        self.title = ""
        self.name = ""
        self.year_of_doctorate = ""
        self.institution = ""
        self.nationality = ""
        self.advisors = set()

        url = "https://genealogy.math.ndsu.nodak.edu/id.php?id=%d" % id_number
        text = requests.get(url, verify=False).text

        self.extract_personal_data(text)
        logger.info("Recovered record: %s %s %s %s",
                    self.name, self.title, self.institution, self.year_of_doctorate)

        if gen >= max_gen:
            return

        txt_start = text.find("Advisor")
        if txt_start == -1:
            logger.error("Failed to find advisor. id=%s, name=%s",
                         self.id_num, self.name)
            return

        txt_stop = text.find("Student")
        adv_text = text[txt_start: txt_stop]

        advs = [int(id_string)
                for id_string in re.findall(r"id.php\?id=(\d+)", adv_text)]

        for adv in advs:
            if adv in node_data:
                self.advised_by(node_data[adv])
            else:
                advisor = Node(adv, gen + 1, max_gen, node_data)
                self.advised_by(advisor)

    def extract_personal_data(self, text):
        """Search the input web page text for bio data."""

        results = re.findall(r"<title>(.+) - The Mathematics Genealogy Project</title>", text)
        if results:
            self.name = results[0]

        results = re.findall(r'<span style="margin-right: 0.5em">(.+)<span style=', text)
        if results:
            self.title = results[0]

        results = re.findall(r'margin-left: 0.5em">(.+)</span>(.+)</span>', text)
        if results:
            self.institution, self.year_of_doctorate = results[0]

    def advised_by(self, other_node):
        """Record an advisor-advisee relationship with another node."""
        self.advisors.add(other_node)

    def dot_string(self, print_advs, brief=True):
        """Emit a dot description for this record."""
        if brief:
            name = textwrap.fill(self.name, 20).replace("\n", "\\n")
            node_str = "node%d[label=\"%s\\n%s\"];\n" % \
                       (self.id_num, name, self.year_of_doctorate)
        else:
            institute = textwrap.fill(self.institution, 25).replace("\n", "\\n")
            node_str = "node%d[label=\"%s\\n%s\\n%s\"];\n" % \
                       (self.id_num, self.name, institute, self.year_of_doctorate)
        if print_advs:
            for adv in self.advisors:
                node_str += "node%d->node%d;\n" % (adv.id_num, self.id_num)

        return node_str


if __name__ == "__main__":
    main()
