from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

############################
#  ID <-> Title Mappings   #
############################
title_to_id = {
    "Analyst": 1,
    "Senior Analyst": 2,
    "Staff Analyst": 3,
    "Data Scientist": 4,
    "Senior Data Scientist": 5,
    "Staff Data Scientist": 6
}
id_to_title = {v: k for k, v in title_to_id.items()}

############################
#  Person <-> ID Mappings  #
############################
person_to_id = {
    "Alice": 101,
    "Bob": 102,
    "Charlie": 103
}
id_to_person = {v: k for k, v in person_to_id.items()}

#################################
#  The main graph (adjacency)   #
#################################
# Keys are node IDs (either a job title ID or a person ID).
# Values are lists of (rel_type, neighbor_id) pairs.
graph = {
    # ---- Job Titles (NEXT_TITLE edges) ----
    # 1 (Analyst) -> 2 (Senior Analyst)
    1: [("NEXT_TITLE", 2)],
    # 2 (Senior Analyst) -> 3 (Staff Analyst)
    2: [("NEXT_TITLE", 3)],
    # 3 (Staff Analyst) -> 4 (Data Scientist)
    3: [("NEXT_TITLE", 4)],
    # 4 (Data Scientist) -> 5 (Senior Data Scientist)
    4: [("NEXT_TITLE", 5)],
    # 5 (Senior Data Scientist) -> 6 (Staff Data Scientist)
    5: [("NEXT_TITLE", 6)],
    # 6 (Staff Data Scientist) -> no next titles
    6: [],

    # ---- People (HELD edges) ----
    # Suppose Alice (101) held Analyst (1), Senior Analyst (2), Staff Analyst (3)
    101: [("HELD", 1), ("HELD", 2), ("HELD", 3),("HELD", 4),("HELD", 5),("HELD", 6)],
    # Bob (102) held Data Scientist (4)
    102: [("HELD", 4)],
    # Charlie (103) held Analyst (1), Senior Analyst (2), Data Scientist (4)
    103: [("HELD", 1), ("HELD", 2), ("HELD", 4)]
}

####################################################
#  Build a separate dictionary of people's paths   #
#  in chronological order (for example, from DB).  #
####################################################
# For demonstration, we hardcode them, but in real usage,
# you'd parse them from the "HELD" edges (with timestamps, etc.).
people_paths = {
    101: [1, 2, 3,4,5,6],   # Alice in chronological order
    102: [4],            # Bob
    103: [1, 2, 4]       # Charlie
}

#Code to parse from the "HELD" edges
# def build_people_paths(graph, id_to_person):
#     """
#     Scans the graph for Person nodes, collects the titles they HELD,
#     and returns a dict: { person_id: [title_ids_in_order] }.

#     Note: This simple version keeps the same order found in 'graph[person_id]'.
#           If you have timestamps, you'd need additional steps to sort them.
#     """
#     people_paths = {}

#     for node_id, edge_list in graph.items():
#         # Check if this node is actually a person
#         # (using 'id_to_person' or any other logic).
#         if node_id in id_to_person:
#             # Collect all title_ids from edges of the form ("HELD", title_id)
#             held_titles = []
#             for (rel_type, neighbor_id) in edge_list:
#                 if rel_type == "HELD":
#                     held_titles.append(neighbor_id)
#             people_paths[node_id] = held_titles

#     return people_paths


########################################################
#    1. Enumerate All Paths from a Start Title (DAG)   #
########################################################
def get_paths_from_title_with_followers(start_title):
    """
    Returns a list of possible paths (as lists of title strings) starting from 'start_title'
    by following 'NEXT_TITLE' edges in the 'graph', along with the names of people
    who followed each path.

    Returns:
        List of dictionaries:
        [
            {
                "path": [<titles>],
                "followers": [<names>]
            }
        ]
    """
    if start_title not in title_to_id:
        return []
    start_id = title_to_id[start_title]

    all_paths_id = []  # will store paths as lists of IDs

    def dfs(current_path):
        current_node = current_path[-1]
        # Filter neighbors to only those with rel_type == "NEXT_TITLE"
        neighbors = [nbr for (rel_type, nbr) in graph.get(current_node, [])
                     if rel_type == "NEXT_TITLE"]

        if not neighbors:
            # leaf node
            all_paths_id.append(current_path.copy())
            return

        for nbr_id in neighbors:
            current_path.append(nbr_id)
            dfs(current_path)
            current_path.pop()

    dfs([start_id])

    # Convert ID paths to string paths and find followers
    result = []

    for pid_list in all_paths_id:
        # Convert path IDs to title strings
        path_titles = [id_to_title[nid] for nid in pid_list]

        # Find people who followed this path
        followers = []
        for person_id, p_path in people_paths.items():
            if is_subsequence(p_path, pid_list):
                followers.append(id_to_person[person_id])

        # Add path and followers to the result
        result.append({
            "path": path_titles,
            "followers": followers
        })

    return result

def is_subsequence(full_path, candidate_path):
    """
    Checks if candidate_path is a subsequence of full_path.
    """
    i = 0  # Pointer for candidate_path
    for job in full_path:
        if i < len(candidate_path) and job == candidate_path[i]:
            i += 1
    return i == len(candidate_path)

################# 2 ################

def get_people_holding_title(title_name):
    """
    Returns a list of people who currently hold the given title.

    Args:
        title_name (str): The title to check for (e.g., "Analyst").

    Returns:
        List of strings: Names of people who currently hold the title.
    """
    title_id = title_to_id.get(title_name)
    if not title_id:
        return []  # Title doesn't exist

    current_holders = []

    for person_id, edges in graph.items():
        # Check if this is a person node
        if person_id in id_to_person:
            # Find the last title held (last "HELD" edge)
            held_titles = [neighbor_id for rel_type, neighbor_id in edges if rel_type == "HELD"]
            if held_titles and held_titles[-1] == title_id:
                current_holders.append(id_to_person[person_id])  # Add person's name

    return current_holders

###################### 3 ##############

def get_titles_held_by_person(person_id):
    """
    Return the titles held by the given person ID as a list of strings.
    """
    if person_id not in people_paths:
        return []
    return [id_to_title[title_id] for title_id in people_paths[person_id]]

##############################################
#                 DEMO SECTION              #
##############################################


# Flask API routes
@app.route('/paths_with_followers/<string:start_title>', methods=['GET'])
def api_get_paths_with_followers(start_title):
    """
    API endpoint to get all possible paths from a given start title and the followers for each path.
    """
    result = get_paths_from_title_with_followers(start_title)
    return jsonify(result)

@app.route('/current_title/<string:title_name>', methods=['GET'])
def api_get_people_holding_title(title_name):
    """
    API endpoint to get all possible paths from a given start title.
    """
    current_title = get_people_holding_title(title_name)
    return jsonify({"title_name": title_name, "current_title": current_title})

@app.route('/titles/<int:person_id>', methods=['GET'])
def api_get_titles_held_by_person(person_id):
    """
    API endpoint to get titles held by a person.
    """
    titles = get_titles_held_by_person(person_id)
    return jsonify({"person_id": person_id, "titles": titles})

if __name__ == '__main__':
    pass
