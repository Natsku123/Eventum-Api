import json
import random
import string


def get_config():
    """
    Read config
    :return:
    """
    with open("config/config.json", "r") as conf:
        data = json.load(conf)

    return data


def get_secret():
    """
    Get secret from config.
    :return:
    """
    with open("config/config.json", "r") as conf:
        data = json.load(conf)

    return data['secret']


def update_config(keys, values):
    """
    Update config with new values.
    :param keys:
    :param values:
    :return:
    """

    # Check that there is the same amount of keys that there is values
    if len(keys) != len(values):
        return False

    # Update config
    data = get_config()
    for i in range(len(keys)):
        data[keys[i]] = values[i]

    # Save config file
    with open("config/config.json", "w") as conf:
        json.dump(data, conf)

    return True


def generate_password(size):
    """
    Generate password with given size.
    :param size:
    :return:
    """
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(size))


def get_json(path):
    """
    Read json file and load it
    :param path:
    :return:
    """
    with open(path, "r") as file:
        data = json.load(file)

    return data


def get_txt(path):
    """
    Read normal text file
    :param path:
    :return:
    """
    with open(path, "r") as file:
        data = file.read()

    return data


def check_extension(filename):
    """
    Check if filename's extension is allowed.
    :param filename:
    :return:
    """
    extensions = set(get_config()['file_extensions'])

    return '.' in filename and filename.rsplit(".", 1)[1].lower() in extensions


# Work around for working with Flask-JWT.
class User:
    def __init__(self, user_id, username, access_token):
        self.id = user_id
        self.username = username
        self.access_token = access_token
