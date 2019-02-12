import datetime
import json
import os
import pymysql
from pymysql import MySQLError
from .utils import get_config, generate_password, get_json, get_txt

# Read configuration from config/config.json
config = get_config()

# Insert configuration in "more readable" format.
database = config['database']
tables = config['tables']

# Tools


def setup_db(sql):
    """
    Setup requires multiple statements with insert.
    :param sql:
    :return:
    """
    # Parse MySQL commands from sql
    sql = sql.split("#")

    # Execute all MySQL commands
    for thing in sql:
        print("Executing: ", thing)
        if not insert(thing):
            return False
        print("Done.")

    return True


def insert(sql):
    """
    Insert given sql into database.
    :param sql:
    :return:
    """
    db = pymysql.connect(database['host'], database['username'],
                         database['password'], database['database'],
                         cursorclass=pymysql.cursors.DictCursor)

    try:
        with db.cursor() as cursor:
            cursor.execute(sql)

        db.commit()
        db.close()
        return True
    except MySQLError as e:

        # Rollback and print error if commit or execute fails.
        db.rollback()
        db.close()
        print(e, e.args)
        return False


def delete_user(user_id):
    """
    Delete user from database.
    :param user_id:
    :return:
    """
    sql = "DELETE FROM {0} WHERE `id`='{1}';".format(tables['users'], user_id)
    return insert(sql)


def get_one(sql):
    """
    Get one object from database with sql.
    :param sql:
    :return:
    """
    db = pymysql.connect(database['host'], database['username'],
                         database['password'], database['database'],
                         cursorclass=pymysql.cursors.DictCursor)

    try:
        with db.cursor() as cursor:
            cursor.execute(sql)
            data = cursor.fetchone()

        db.close()
        return data
    except MySQLError:

        # Return None if fails
        db.close()
        return None


def get_all(sql):
    """
    Get all objects from database with sql.
    :param sql:
    :return:
    """
    db = pymysql.connect(database['host'], database['username'],
                         database['password'], database['database'],
                         cursorclass=pymysql.cursors.DictCursor)

    try:
        with db.cursor() as cursor:
            cursor.execute(sql)
            data = cursor.fetchall()

        db.close()
        return data
    except MySQLError:

        # Return None if fails
        db.close()
        return None


def get_newest(table):
    """
    Get object with highest ID.
    :param table:
    :return:
    """
    sql = "SELECT MAX(id) FROM {0};".format(table)

    # Return the ID.
    return get_one(sql)['MAX(id)']


def get_last_updated():
    """
    Get last updated event.
    :return:
    """
    sql = "SELECT MAX(updated) FROM {0};".format(tables['events'])
    return get_one(sql)


# Authentication

def create_user(username):
    """
    Create password to be used in authentication.
    :param username:
    :return:
    """
    password = generate_password(64)

    # Hash the password while insterting to database
    sql = "INSERT INTO {0} (`password`, `username`) VALUES " \
          "(ENCRYPT('{1}', CONCAT('$6$', SUBSTRING(SHA(RAND()), -16)))," \
          " '{2}');".format(tables['users'], password, username)
    if insert(sql):
        return password
    else:
        return {'Error': 'Cannot create password.'}


def update_user(user_id):
    """
    Regenerate password.
    :param user_id:
    :return:
    """
    password = generate_password(64)
    user = get_user(user_id, True)

    # Hash the password while inserting to database
    sql = "UPDATE `{0}` SET `password`=ENCRYPT('{1}', " \
          "CONCAT('$6$', SUBSTRING(SHA(RAND()), -16))), `username`='{2}' " \
          "WHERE `id`='{3}';".format(
            tables['users'], password, user['username'], user_id)
    if insert(sql):
        return password
    else:
        return {'Error': 'Cannot update password.'}


def get_user(search, useId=False):
    """
    Get user for JWT. Search alone is user_id and
    if useId is True, search is username.
    :param search:
    :param useId:
    :return:
    """
    if useId:
        sql = "SELECT * FROM {0} WHERE `id`='{1}';".format(
            tables['users'], search)
    else:
        sql = "SELECT * FROM {0} WHERE `user`='{1}';".format(
            tables['users'], search)
    return get_one(sql)


def get_users():
    """
    Get all users for JWT.
    :return:
    """
    sql = "SELECT * FROM {0};".format(tables['users'])
    return get_all(sql)


def login(username, password):
    """
    Check if username and password are valid.
    :param username:
    :param password:
    :return:
    """

    # Compare with MySQL's Encrypt -function.
    sql = "SELECT * FROM {0} WHERE `password`=ENCRYPT('{1}', `password`) " \
          "AND `username`='{2}';".format(tables['users'], password, username)
    return get_one(sql)


# Events


def get_events():
    """
    Get all events.
    :return:
    """
    sql = "SELECT * FROM {0};".format(tables['events'])
    events = get_all(sql)
    for event in events:
        # Delete participators if
        # event's sign up has expired over 30 days ago.
        if datetime.timedelta(days=30) < (datetime.datetime.utcnow().date() -
                                          event['expire']):
            delete_participants(event['id'])
        else:
            # Simplify returned events
            del event['template']
            del event['description']
    return events


def get_event(event_id, participants=False, simple=False):
    """
    Get one event based on event_id.
    :param event_id:
    :param participants:
    :param simple:
    :return:
    """
    sql = "SELECT * FROM {0} WHERE `id`={1};".format(
        tables['events'], event_id)
    event = get_one(sql)
    if participants:

        # Delete participators if event's sign up has expired over 30 days ago.
        if datetime.timedelta(days=30) < (datetime.datetime.utcnow().date() -
                                          event['expire']):
            delete_participants(event['id'])
        else:
            # Add participators to event
            participants = get_participants(event['id'])
            event['participants'] = participants

    if not simple:
        # Add non-simple elements to event
        event['limits'] = get_limits(event['id'])
        event['prices'] = get_prices(event['id'])
        event['template'] = get_json(event['template'])

        # Get description for event if exists.
        if event['description'] is not None:
            event['description'] = get_txt(event['description'])
        else:
            event['description'] = ""
    else:
        del event['template']
        del event['description']

    return event


def create_event(name, template, expire, description, available):
    """
    Create event based on given info and create template file for it.
    :param name:
    :param template:
    :param expire:
    :param description:
    :param available:
    :return:
    """

    # Get file locations for template and description.
    template_file = os.path.join(config['json']['templates'], str(
        get_newest(tables['events'])+1) + "_" + name + ".json")
    description_file = os.path.join(config['event_description_root'], str(
        get_newest(tables['events'])+1)+"_"+name+".txt")

    # Create event directory to store forms
    directory = os.path.join(config['json']['form_root'], str(
        get_newest(tables['events'])+1) + "_" + name)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Store template in JSON format and description in normal text format
    with open(template_file, "w") as file:
        json.dump(template, file)
    with open(description_file, "w") as d_file:
        d_file.write(description)

    # Insert event to database
    updated = datetime.datetime.now()
    sql = "INSERT INTO {0} (`name`, `template`, `updated`, " \
          "`expire`, `description`, `available`) VALUES ('{1}', " \
          "'{2}', '{3}', '{4}', '{5}', '{6}');".format(
            tables['events'], name, template_file, updated, expire,
            description_file, available)

    if insert(sql):
        return get_event(get_newest(tables['events']))
    else:
        return {'Error': 'Unable to create event.'}


def event_available(event_id, available):
    """
    Change event availability.
    :param event_id:
    :param available:
    :return:
    """
    updated = datetime.datetime.now()
    sql = "UPDATE {0} SET `available`='{1}', `updated`='{2}' " \
          "WHERE `id`='{3}';".format(
            tables['events'], available, updated, event_id)

    if insert(sql):
        return get_event(event_id)
    else:
        return {'Error': 'Unable to change event availability.'}


def update_event(event_id, name, template, expire, description, available):
    """
    Update existing event.
    :param event_id:
    :param name:
    :param template:
    :param expire:
    :param description:
    :param available:
    :return:
    """
    old_event = get_event(event_id)

    # Get old event's template
    with open(old_event['template'], "r") as t_read:
        old_template = t_read

    # Compare templates
    if template != old_template:
        with open(old_event['template'], "w") as file:
            json.dump(template, file)

    # Get old event's description
    with open(old_event['description'], "r") as d_read:
        old_description = d_read.read()

    # Compare descriptions
    if description != old_description:
        with open(old_event['description'], "w") as d_file:
            d_file.write(description)

    updated = datetime.datetime.now()
    sql = "UPDATE `{0}` SET `name`='{1}', `updated`='{2}', " \
          "`expire`='{3}', `available`='{4}' WHERE `id`='{5}';".format(
        tables['events'], name, updated, expire, available, event_id)

    if insert(sql):
        return {'id': event_id, 'name': name, 'template': template,
                'description': description, 'updated': updated,
                'expire': expire}
    else:
        return {'Error': 'Unable to update event.'}


def get_image(event_id):
    """
    Get one image based on event_id.
    :param event_id:
    :return:
    """
    sql = "SELECT * FROM {0} WHERE `event_id`='{1}';".format(
        tables['eventImages'], event_id)

    return get_one(sql)


def add_image(event_id, url):
    """
    Create new image for event based on event_id.
    :param event_id:
    :param url:
    :return:
    """
    sql = "INSERT INTO {0} (`event_id`, `image`) VALUES ('{1}', '{2}');"\
        .format(tables["eventImages"], event_id, url)

    if insert(sql):
        return get_image(event_id)
    else:
        return {'Error': "Unable to create image."}


def update_image(image_id, event_id, url):
    """
    Edit existing image.
    :param image_id:
    :param event_id:
    :param url:
    :return:
    """
    sql = "UPDATE `{0}` SET `event_id`='{1}', `image`='{2}' WHERE `id`='{3}';"\
        .format( tables["eventImages"], event_id, url, image_id)

    if insert(sql):
        return get_image(event_id)
    else:
        return {'Error': "Unable to create image."}

# Participants


def get_participants(participant_id, fetchForm=False):
    """
    Get one events participants based on event_id.
    :param participant_id:
    :param fetchForm:
    :return:
    """
    sql = "SELECT * FROM {0} WHERE `event_id`={1};".format(
        tables['eventParticipants'], participant_id)

    humans = []
    connections = get_all(sql)

    # Convert participators to humans.
    for connection in connections:
        human = get_human(connection['human_id'])
        human['paid'] = connection['paid']
        human['participation_id'] = connection['id']

        # Get form for current event, if wanted
        if fetchForm:
            human['form'] = get_json(connection['form'])

        humans.append(human)

    return humans


def get_participant(participant_id):
    """
    Get one participant based on id.
    :param participant_id:
    :return:
    """

    sql = "SELECT * FROM {0} WHERE `id`='{1}';".format(
        tables['eventParticipants'], participant_id)

    participant = get_one(sql)

    # Get form for participant
    participant['form'] = get_json(participant['form'])

    return participant


def add_participants(event_id, form):
    """
    Add human to participate in an event.
    :param event_id:
    :param form:
    :return:
    """

    # Check if human with this email exists
    # And create a new one, if doesn't
    human = get_human(None, form['email'])
    if human is None:
        human = create_human(form['name'], form['email'])
    else:

        # Check if human is already in the event.
        participants = get_participants(event_id)
        for participant in participants:
            if participant['id'] == human['id']:
                return {'Error': 'Already in event.'}

    # If human is for some reason still not created
    if human is None:
        return {'Error': 'Human cannot be found.'}
    elif 'Error' in human:
        return human

    # Create file for form
    form_file = os.path.join(config['json']['form_root'], str(event_id) + "_" + get_event(event_id)['name'] + "/" + human['name'] + ".json")

    with open(form_file, "w") as file:
        json.dump(form, file)

    sql = "INSERT INTO {0} (`event_id`, `human_id`, `form`, `paid`) " \
          "VALUES ('{1}', '{2}', '{3}', 0);".format(
            tables['eventParticipants'], event_id, human['id'], form_file)

    if insert(sql):
        return get_participant(get_newest(tables['eventParticipants']))
    else:
        return {'Error': 'Cannot add to event.'}


def delete_participants(event_id):
    """
    Delete old participants of event.
    :param event_id:
    :return:
    """
    participants = get_participants(event_id)

    # Delete participants if there is any
    if len(participants) > 0:
        for participant in participants:

            # Delete participation record if participant has paid
            if participant['paid'] is not None and participant['paid'] > 0:
                try:
                    os.remove(participant['form'])
                except OSError:
                    print(' -- WARNING! Unable to delete',
                          participant['form'], "--")
                sql = "DELETE FROM {0} WHERE `id`='{1}';"\
                    .format(tables['eventParticipants'],
                            participant['participantion_id'])
                if not insert(sql):
                    print(' -- WARNING! Unable to delete participant with ID:',
                          participant['participantion_id'], "--")


def changePay(participation_id, status):
    """
    Change the status of payment.
    :param participation_id:
    :param status:
    :return:
    """
    sql = "UPDATE `{0}` SET `paid`='{1}' WHERE `id`='{2}';".format(
        tables['eventParticipants'], status, participation_id)

    if insert(sql):
        return get_one("SELECT * FROM {0} WHERE `id`='{1}';".format(
            tables['eventParticipants'], participation_id))
    else:
        return {'Error': 'Unable to change the status of payment'}


def get_my_events(human_id):
    """
    Get all events human has participated based on human_id.
    :param human_id:
    :return:
    """
    sql = "SELECT * FROM {0} WHERE `human_id`={1};".format(
            tables['eventParticipants'], human_id)

    events = []
    connections = get_all(sql)
    for connection in connections:
        events.append(get_event(connection['event_id']))

    return events


# Humans / Users


def get_human(human_id, email=None):
    """
    Get one human based on human_id or email.
    :param human_id:
    :param email:
    :return:
    """
    if human_id is None and email is not None:
        sql = "SELECT * FROM {0} WHERE `email`='{1}';".format(
            tables['humans'], email)
    else:
        sql = "SELECT * FROM {0} WHERE `id`={1};".format(
            tables['humans'], human_id)

    human = get_one(sql)

    if human is not None:

        # Get role for human based on its role_id
        human['role'] = get_role(human['role_id'])
        del human['role_id']

    return human


def create_human(name, email):
    """
    Create human and check if member of Skilta.
    :param name:
    :param email:
    :return:
    """
    memberlist = config['json']['memberlist']
    isMember = False

    with open(memberlist, "r") as file:
        data = json.load(file)

    # Check if email exists in memberlist
    for member in data:
        for value in list(member.values()):

            if value == email:
                isMember = True
                break

    roles = get_roles()

    # Assign role based on result of the memberlist check
    if isMember:
        role_id = 0
        for role in roles:

            # Role with power 3 is used as a member role.
            if role['power'] == 3:
                role_id = role['id']
                break
    else:
        role_id = 0
        for role in roles:

            # Role with power 1 is used as an 'other' role.
            if role['power'] == 1:
                role_id = role['id']
                break

    sql = "INSERT INTO {0} (`name`, `email`, `signed`, `role_id`) " \
          "VALUES ('{1}', '{2}', '{3}', '{4}');".format(
            tables['humans'], name, email, datetime.datetime.now(), role_id)

    if insert(sql):
        return get_human(None, email)
    else:
        return {'Error': 'Cannot create human.'}


def update_human(human_id, name, email):
    """
    Update existing human.
    :param human_id:
    :param name:
    :param email:
    :return:
    """
    sql = "UPDATE `{0}` SET `name`='{1}', `email`='{2}' WHERE `id`='{3}';"\
        .format(tables['humans'], name, email, human_id)

    if insert(sql):
        return get_human(human_id)
    else:
        return {'Error': 'Unable to update human.'}


# Roles


def get_role(id):
    """
    Get one role based on id.
    :param id:
    :return:
    """
    sql = "SELECT * FROM {0} WHERE `id`={1};".format(tables['roles'], id)

    return get_one(sql)


def get_roles():
    """
    Get all roles.
    :return:
    """
    sql = "SELECT * FROM {0};".format(tables['roles'])

    return get_all(sql)


def create_role(name, power):
    """
    Create new role.
    :param name:
    :param power:
    :return:
    """
    sql = "INSERT INTO {0} (`name`, `power`) VALUES ('{1}', '{2}');"\
        .format(tables['roles'], name, power)

    if insert(sql):
        return get_role(get_newest(tables['roles']))
    else:
        return {'Error': 'Unable to create role.'}


def update_role(role_id, name, power):
    """
    Update an existing role.
    :param role_id:
    :param name:
    :param power:
    :return:
    """
    sql = "UPDATE `{0}` SET `name`='{1}', `power`='{2}' WHERE `id`='{3}';"\
        .format(tables['roles'], name, power, role_id)

    if insert(sql):
        return get_role(role_id)
    else:
        return {'Error': 'Unable to update role.'}


# Prices


def get_price(event_id, role_id):
    """
    Get price for certain role in certain event.
    :param event_id:
    :param role_id:
    :return:
    """
    sql = "SELECT * FROM {0} WHERE `event_id`={1} AND `role_id`={2};"\
        .format(tables['prices'], event_id, role_id)

    price = get_one(sql)

    # Get simplified event for the price and role
    # Based on event_id and role_id
    price['event'] = get_event(price['event_id'], False, True)
    del price['event_id']
    price['role'] = get_role(price['role_id'])
    del price['role_id']

    return price


def get_prices(event_id):
    """
    Get prices for certain event.
    :param event_id:
    :return:
    """
    sql = "SELECT * FROM {0} WHERE `event_id`={1};"\
        .format(tables['prices'], event_id)

    prices = get_all(sql)

    for price in prices:

        # Replace role_id with actual role
        price['role'] = get_role(price['role_id'])
        del price['role_id']

    return prices


def create_price(event_id, role_id, price):
    """
    Create price for event based on role.
    :param event_id:
    :param role_id:
    :param price:
    :return:
    """
    sql = "INSERT INTO {0} (`event_id`, `role_id`, `price`)" \
          " VALUES ('{1}', '{2}', '{3}');".format(
            tables['prices'], event_id, role_id, price)

    if insert(sql):
        return get_price(event_id, role_id)
    else:
        return {'Error': 'Could not create price.'}


def update_price(price_id, event_id, role_id, price):
    """
    Update existing price.
    :param price_id:
    :param event_id:
    :param role_id:
    :param price:
    :return:
    """
    sql = "UPDATE `{0}` SET `event_id`='{1}', `role_id`='{2}', " \
          "`price`='{3}' WHERE `id`='{4}';".format(
            tables['prices'], event_id, role_id, price, price_id)

    if insert(sql):
        return get_price(event_id, role_id)
    else:
        return {'Error': 'Unable to update price.'}


def get_limits(event_id):
    """
    Get participant limits for certain event. And calculate how many filled.
    :param event_id:
    :return:
    """

    # Get the limits from database.
    sql = "SELECT * FROM {0} WHERE `event_id`={1};"\
        .format(tables['limits'], event_id)

    limits = get_all(sql)

    # Get needed objects for calculation of filled limits
    roles = get_roles()
    participants = get_participants(event_id)
    overflow = []

    for role in roles:
        role['participants'] = []
        role['hasLimit'] = 0

        # Gather participants with this role
        for participant in participants:
            if participant['role']['id'] == role['id']:
                role['participants'].append(participant)

        # Check if there is limit for role
        for limit in limits:
            if limit['role_id'] == role['id']:
                role['hasLimit'] = limit['id']

    # Fill limits for roles other than role with power 1
    for role in roles:
        if role['hasLimit'] > 0 and role['power'] != 1:
            limit = get_limit(role['hasLimit'])
            if len(role['participants']) <= limit['size']:
                if not fill_limit(role['hasLimit'], len(role['participants'])):
                    print(' -- WARNING! Unable to fill limit with ID:',
                          role['hasLimit'], "--")
            else:
                used = role['participants'][:limit['size']]
                delta = limit['size'] - len(role['participants'])
                if not fill_limit(role['hasLimit'], len(used)):
                    print(' -- WARNING! Unable to fill limit with ID:',
                          role['hasLimit'], "--")
                overflow = overflow + role['participants'][delta:]
        elif role['power'] != 1:
            overflow = overflow + role['participants']

    # Search role with power 1 (Is used as role 'Other')
    for role in roles:
        if role['power'] == 1 and role['hasLimit'] > 0:
            limit = get_limit(role['hasLimit'])

            # Update database based on overflow
            if len(overflow) > 0:
                role['participants'] = role['participants'] + overflow

                # Reset overflow
                overflow = []

                # Update filled size of limit to database
                if len(role['participants']) <= limit['size']:
                    if not fill_limit(role['hasLimit'],
                                      len(role['participants'])):
                        print(' -- WARNING! Unable to fill limit with ID:',
                              role['hasLimit'], "--")
                else:
                    used = role['participants'][:limit['size']]
                    delta = limit['size'] - len(role['participants'])
                    if not fill_limit(role['hasLimit'], len(used)):
                        print(' -- WARNING! Unable to fill limit with ID:',
                              role['hasLimit'], "--")
                    overflow = overflow + role['participants'][delta:]
            else:
                if len(role['participants']) <= limit['size']:
                    if not fill_limit(role['hasLimit'],
                                      len(role['participants'])):
                        print(' -- WARNING! Unable to fill limit with ID:',
                              role['hasLimit'], "--")

    limits = get_all(sql)

    for limit in limits:

        # Replace role_id with actual role
        limit['role'] = get_role(limit['role_id'])
        del limit['role_id']

    # If some overflow still exists (shouldn't), add it as a limit
    if len(overflow) > 0:
        limits.append({'role': {'name': 'overflow'}, "size": len(overflow),
                       "filled": len(overflow)})

    return limits


def get_limit(first_id, second_id=None):
    """
    Get one specific limit. First_id alone is limit_id and
    both together are event_id and role_id.
    :param first_id:
    :param second_id:
    :return:
    """
    if second_id is None:
        sql = "SELECT * FROM {0} WHERE `id`={1};"\
            .format(tables['limits'], first_id)
    else:
        sql = "SELECT * FROM {0} WHERE `event_id`={1} AND `role_id`={2};"\
            .format(tables['limits'], first_id, second_id)

    limit = get_one(sql)

    # Replace event_id and role_id with actual event and role
    limit['event'] = get_event(limit['event_id'], False, True)
    del limit['event_id']
    limit['role'] = get_role(limit['role_id'])
    del limit['role_id']

    return limit


def create_limit(event_id, size, role_id=None):
    """
    Create new limit for event.
    :param event_id:
    :param size:
    :param role_id:
    :return:
    """
    if role_id is None:
        sql = "INSERT INTO {0} (`event_id`, `size`) VALUES ('{1}', '{2}');"\
            .format(tables['limits'], event_id, size)
    else:
        sql = "INSERT INTO {0} (`event_id`, `role_id`, `size`) " \
              "VALUES ('{1}', '{2}', '{3}');".format(
                tables['limits'], event_id, role_id, size)

    if insert(sql):
        return get_limit(get_newest(tables['limits']))
    else:
        return {'Error': 'Unable to create limit.'}


def update_limit(limit_id, event_id, size, role_id=None):
    """
    Update existing limit.
    :param limit_id:
    :param event_id:
    :param size:
    :param role_id:
    :return:
    """
    if role_id is None:
        sql = "UPDATE `{0}` SET `event_id`='{1}', `size`='{2}' " \
              "WHERE `id`='{3}';".format(
                tables['limits'], event_id, size, limit_id)
    else:
        sql = "UPDATE `{0}` SET `event_id`='{1}', `role_id`='{2}', " \
              "`size`='{3}' WHERE `id`='{4}';".format(
                tables['limits'], event_id, role_id, size, limit_id)

    if insert(sql):
        return get_limit(limit_id)
    else:
        return {'Error': 'Unable to update limit.'}


def fill_limit(limit_id, filled):
    """
    Fill limit when checked.
    :param limit_id:
    :param filled:
    :return:
    """
    sql = "UPDATE `{0}` SET `filled`='{1}' WHERE `id`='{2}';"\
        .format(tables['limits'], filled, limit_id)

    return insert(sql)
