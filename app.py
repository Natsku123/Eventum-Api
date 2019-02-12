from flask import Flask, jsonify, abort, make_response, request

# For manual checking of user without wrapping,
# we need to use protected member from Flask-JWT :/
from flask_jwt import JWT, jwt_required, current_identity, _jwt_required
from flask_cors import CORS, cross_origin
from werkzeug.utils import secure_filename
from modules.database import *
from modules.utils import update_config, get_json, get_secret, User, \
    check_extension

app = Flask(__name__)
app.config['SECRET_KEY'] = get_secret()
app.config['JWT_EXPIRATION_DELTA'] = datetime.timedelta(hours=3)
app.config['UPLOAD_FOLDER'] = config['media_root']
cors = CORS(app, supports_credentials=True)


def unauthorized():
    """
    Returns response for unauthorized access.
    :return:
    """
    return make_response(jsonify({'error': 'Unauthorized access'}), 401)


def authenticate(username, password):
    """
    Authenticate user if exists.
    :param username:
    :param password:
    :return:
    """
    user = login(username, password)

    if user:
        return User(user['id'], user['username'], user['password'])


def identity(payload):
    """
    Get user from payload.
    :param payload:
    :return:
    """
    user_id = payload['identity']

    return get_user(user_id, True)


jwt = JWT(app, authenticate, identity)


@app.route('/')
def root():
    """
    API root.
    :return:
    """

    # TODO
    # Add documentation here

    return 'Welcome to Eventum-API!'


@app.route('/setup/', methods=['GET'])
def setup():

    # Check if setup has already been done.
    if not get_config()['setup_done']:

        # Get database setup script from config folder.
        with open("config/database/init_database.sql", "r") as sql_file:
            sql = sql_file.read()

        # Run database setup.
        if setup_db(sql):
            if update_config(["setup_done"], [True]):
                return "Setup and config update succeeded."
            else:
                return "Setup succeeded but config update didn't."
        else:
            return "Setup failed."


@app.route('/v1.0/tokens/create/', methods=['POST'])
@jwt_required()
def new_user():
    """
    Create new user
    :return:
    """
    if not request.json or 'username' not in request.json:
        abort(400)

    # Create new user
    response = create_user(request.json['username'])

    return jsonify({'password': response,
                    'username': request.json['username']})


@app.route('/v1.0/users/', methods=['GET'])
@jwt_required()
def all_users():
    """
    Get all users
    :return:
    """
    users = get_users()

    for user in users:
        del user['password']

    return jsonify(users)


@app.route('/v1.0/users/<int:user_id>/', methods=['GET'])
@jwt_required()
def user_by_id(user_id):
    """
    Get user based on id
    :param user_id:
    :return:
    """
    user = get_user(user_id, True)

    del user['password']

    return jsonify(user)


@app.route('/v1.0/users/<int:user_id>/update/', methods=['POST'])
@jwt_required()
def update_pwd(user_id):
    """
    Update password for user based on user_id.
    :param user_id:
    :return:
    """
    if not request.json or 'username' not in request.json:
        abort(400)

    response = update_user(user_id)
    return jsonify({'password': response,
                    'username': get_user(user_id, True)['username']})


@app.route('/v1.0/users/<int:user_id>/delete/', methods=['DELETE'])
@jwt_required()
def remove_user(user_id):
    """
    Delete user based on user_id.
    :param user_id:
    :return:
    """
    user = get_user(user_id, True)

    return jsonify({'username': user['username'],
                    'deleted': delete_user(user_id)})


@app.route('/v1.0/event/<int:event_id>/', methods=['GET'])
def event(event_id):
    """
    Get event based on event_id
    :param event_id:
    :return:
    """
    return jsonify({'event': get_event(event_id, False)})


@app.route('/v1.0/events/', methods=['GET', 'POST'])
@cross_origin()
def events():
    """
    Interface for usage with parameters for events
    :return:
    """
    event_id = request.args.get('event_id')

    # Check request method
    if request.method == "GET":
        if event_id is not None:

            # Getting participants with event need authorization
            if request.args.get('participants') == "true":
                _jwt_required(app.config['JWT_DEFAULT_REALM'])

            return jsonify(get_event(event_id, current_identity is not None))

        return jsonify(get_events())
    else:
        # All POST request for events need authorization
        _jwt_required(app.config['JWT_DEFAULT_REALM'])

        if current_identity is None:
            return unauthorized()
        else:
            mode = request.args.get('mode')
            available = request.args.get('available')

            # Do something based on mode
            if mode is None or mode == "new":

                # Create event if everything is provided
                if not request.json or 'name' not in request.json or \
                        'template' not in request.json or \
                        'expire' not in request.json or \
                        'available' not in request.json:
                    abort(400)

                return jsonify(create_event(request.json['name'],
                                            request.json['template'],
                                            request.json['expire'],
                                            request.json['description'],
                                            request.json['available']))

            elif mode == "edit" and event_id is not None:

                # Edit event with things provided
                if not request.json:
                    abort(400)

                old_event = get_event(event_id)
                if 'name' not in request.json:
                    name = old_event['name']
                else:
                    name = request.json['name']

                if 'template' not in request.json:
                    template = get_json(old_event['template'])
                else:
                    template = request.json['template']

                if 'expire' not in request.json:
                    expire = old_event['expire']
                else:
                    expire = request.json['expire']

                if 'description' not in request.json:
                    description = old_event['description']
                else:
                    description = request.json['description']

                if 'available' not in request.json:
                    available = old_event['available']
                else:
                    available = request.json['available']

                return jsonify(update_event(event_id, name, template, expire,
                                            description, available))

            elif event_id is not None and available is not None:

                # Change event's availability
                return jsonify(event_available(event_id, available))

            else:
                abort(400)


@app.route('/v1.0/event/<int:event_id>/edit/', methods=['POST'])
@jwt_required()
def edit_event(event_id):
    """
    Non-parameter interface for editing events.
    :param event_id:
    :return:
    """
    if not request.json:
        abort(400)

    old_event = get_event(event_id)
    if 'name' not in request.json:
        name = old_event['name']
    else:
        name = request.json['name']

    if 'template' not in request.json:
        template = get_json(old_event['template'])
    else:
        template = request.json['template']

    if 'expire' not in request.json:
        expire = old_event['expire']
    else:
        expire = request.json['expire']

    if 'description' not in request.json:
        description = get_txt(old_event['description'])
    else:
        description = request.json['description']

    if 'available' not in request.json:
        available = old_event['available']
    else:
        available = request.json['available']

    return jsonify({'event': update_event(event_id, name, template, expire,
                                          description, available)})


@app.route('/v1.0/event/create/', methods=['POST'])
@jwt_required()
def new_event():
    """
    Non-parameter interface for creating new events.
    :return:
    """
    if not request.json or 'name' not in request.json or \
            'template' not in request.json or \
            'expire' not in request.json or 'available' not in request.json:
        abort(400)

    if 'description' not in request.json:
        description = ""
    else:
        description = request.json['description']

    return jsonify({'event': create_event(request.json['name'],
                                          request.json['template'],
                                          request.json['expire'],
                                          description,
                                          request.json['available'])})


@app.route('/v1.0/events/newest/', methods=['GET'])
@cross_origin()
def newest_event():
    """
    Get newest event
    :return:
    """
    return jsonify({'newest': get_newest(tables['events'])})


@app.route('/v1.0/humans/', methods=['GET'])
@jwt_required()
@cross_origin()
def param_humans():
    """
    Interface for usage with parameters for humans
    :return:
    """
    human_id = request.args.get('human_id')
    mode = request.args.get('events')

    if mode is None or mode == 0 and human_id is not None:

        # Get human with human_id
        return jsonify({'human': get_human(human_id)})

    elif mode == 1 and human_id is not None:

        # Get events that human with human_id has participated
        return jsonify({'events': get_my_events(human_id)})

    else:
        return jsonify({'error': 'Use parameters in this url.'})


@app.route('/v1.0/human/<int:human_id>/', methods=['GET'])
@jwt_required()
def human(human_id):
    """
    Non-parameter interface for getting a human based on human_id.
    :param human_id:
    :return:
    """
    return jsonify({'human': get_human(human_id)})


@app.route('/v1.0/human/<int:human_id>/events/', methods=['GET'])
@jwt_required()
def human_events(human_id):
    """
    Non-parameter interface for getting events
    human based on human_id has participated.
    :param human_id:
    :return:
    """
    return jsonify({'events': get_my_events(human_id)})


@app.route('/v1.0/participants/', methods=['POST', 'GET'])
@cross_origin()
def param_participants():
    """
    Interface for usage with parameters for participants.
    :return:
    """
    event_id = request.args.get('event_id')
    participation_id = request.args.get('participant_id')
    mode = request.args.get("mode")

    # Check request method
    if request.method == "POST":

        # Do something based on mode
        if mode == "pay" and participation_id is not None:

            # Changing payment status needs authorization
            _jwt_required(app.config['JWT_DEFAULT_REALM'])
            if current_identity is None:
                return unauthorized()

            # Change payment status
            return jsonify(changePay(participation_id, 1))
        elif mode == "unpay" and participation_id is not None:

            # Changing payment satus need authorization
            _jwt_required(app.config['JWT_DEFAULT_REALM'])
            if current_identity is None:
                return unauthorized()

            # Change payment status
            return jsonify(changePay(participation_id, 0))
        elif event_id is not None:

            # Add participation for event if form is provided
            if not request.json or 'form' not in request.json:
                abort(400)

            return jsonify(add_participants(event_id,  request.json['form']))
    else:

        # All GET requests need authorization
        _jwt_required(app.config['JWT_DEFAULT_REALM'])
        if current_identity is None:
            return unauthorized()

        # Get participants if event_id is provided
        if event_id is not None:
            return jsonify(get_participants(event_id, True))
        else:
            abort(400)


@app.route('/v1.0/event/<int:event_id>/participant/add/', methods=['POST'])
def participant_add(event_id):
    """
    Non-parameter interface for adding participants to event based on event_id
    :param event_id:
    :return:
    """
    if not request.json or 'form' not in request.json:
        abort(400)

    return jsonify({'participant': add_participants(event_id,
                                                    request.json['form'])})


@app.route('/v1.0/participant/<int:participation_id>/payment/<int:status>',
           methods=['POST'])
@jwt_required()
def participant_paid(participation_id, status):
    """
    Non-parameter interface for changing
    payment status of participant with participation_id.
    :param participation_id:
    :param status:
    :return:
    """
    return jsonify({'participant': changePay(participation_id, status)})


@app.route('/v1.0/roles/', methods=['GET', 'POST'])
@cross_origin()
def params_roles():
    """
    Interface for usage with parameters for roles.
    :return:
    """
    role_id = request.args.get('role_id')

    # Check request method
    if request.method == "POST":

        # All POST requests need authorization
        _jwt_required(app.config['JWT_DEFAULT_REALM'])
        if current_identity is None:
            return unauthorized()
        else:
            mode = request.args.get('mode')

            # Do something based on mode
            if mode is None or mode == "new":

                # Create new role if everything is provided
                if not request.json or 'name' not in request.json or \
                        'power' not in request.json:
                    abort(400)

                return jsonify(create_role(request.json['name'],
                                           request.json['power']))

            elif mode == "edit" and role_id is not None:

                # Edit role with information provided
                if not request.json:
                    abort(400)

                old = get_role(role_id)
                new = {}
                if 'name' not in request.json:
                    new['name'] = old['name']
                else:
                    new['name'] = request.json['name']

                if 'power' not in request.json:
                    new['power'] = old['power']
                else:
                    new['power'] = request.json['power']

                return jsonify(update_role(role_id, new['name'], new['power']))

    else:

        # Return role if role_id is provided, otherwise return all roles
        if role_id is not None:
            return jsonify(get_role(role_id))
        else:
            return jsonify(get_roles())


@app.route('/v1.0/role/<int:role_id>/', methods=['GET'])
def role(role_id):
    """
    Non-parameter interface for getting role.
    :param role_id:
    :return:
    """
    return jsonify({'role': get_role(role_id)})


@app.route('/v1.0/roles/create/', methods=['POST'])
@jwt_required()
def new_role():
    """
    Non-parameter interface for creation of new roles.
    :return:
    """
    if not request.json or 'name' not in request.json or \
            'power' not in request.json:
        abort(400)
    return jsonify({'role': create_role(request.json['name'],
                                        request.json['power'])})


@app.route('/v1.0/role/<int:role_id>/edit/', methods=['POST'])
@jwt_required()
def edit_role(role_id):
    """
    Non-parameter interface for editing existing events.
    :param role_id:
    :return:
    """
    if not request.json:
        abort(400)

    old = get_role(role_id)
    new = {}
    if 'name' not in request.json:
        new['name'] = old['name']
    else:
        new['name'] = request.json['name']

    if 'power' not in request.json:
        new['power'] = old['power']
    else:
        new['power'] = request.json['power']

    return jsonify({'role': update_role(role_id, new['name'], new['power'])})


@app.route('/v1.0/prices/', methods=['GET', 'POST'])
@cross_origin()
def param_prices():
    """
    Interface for usage with parameters for prices.
    :return:
    """
    event_id = request.args.get('event_id')
    role_id = request.args.get('role_id')

    # Check request method
    if request.method == "POST":

        # All POST request need authorization
        _jwt_required(app.config['JWT_DEFAULT_REALM'])
        if current_identity is None:
            return unauthorized()
        else:
            mode = request.args.get('mode')

            # Do something based on mode
            if mode is None or mode == "new":

                # Create new price if everything is provided
                if not request.json or 'role_id' not in request.json or \
                        'price' not in request.json:
                    abort(400)

                return jsonify(create_price(event_id, request.json['role_id'],
                                            request.json['price']))

            elif mode == "edit" and role_id is not None:

                # Edit price with information provided
                if not request.json:
                    abort(400)

                old = get_price(event_id, role_id)
                if 'price' in request.json:
                    old['price'] = request.json['price']

                return jsonify(update_price(old['id'], event_id, role_id,
                                            old['price']))
    else:

        # Return all prices for event based on event_id
        # if role_id doesn't exist, otherwise return price based on both
        if role_id is None:
            return jsonify(get_prices(event_id))

        return jsonify(get_price(event_id, role_id))


@app.route('/v1.0/event/<int:event_id>/prices/', methods=['GET'])
def prices(event_id):
    """
    Non-parameter interface for getting prices of event with event_id.
    :param event_id:
    :return:
    """
    return jsonify({'prices': get_prices(event_id)})


@app.route('/v1.0/event/<int:event_id>/role/<int:role_id>/price/',
           methods=['GET'])
def price(event_id, role_id):
    """
    Non-parameter interface for getting price for
    event based on event_id with role_id.
    :param event_id:
    :param role_id:
    :return:
    """
    return jsonify({'price': get_price(event_id, role_id)})


@app.route('/v1.0/event/<int:event_id>/price/create/', methods=['POST'])
@jwt_required()
def new_price(event_id):
    """
    Non-parameter interface for creation of new prices for event with event_id.
    :param event_id:
    :return:
    """
    if not request.json or 'role_id' not in request.json or \
            'price' not in request.json:
        abort(400)

    return jsonify({'price': create_price(event_id, request.json['role_id'],
                                          request.json['price'])})


@app.route('/v1.0/event/<int:event_id>/role/<int:role_id>/price/edit/',
           methods=['POST'])
@jwt_required()
def edit_price(event_id, role_id):
    """
    Non-parameter interface for editing existing price
    for event with event_id and role with role_id.
    :param event_id:
    :param role_id:
    :return:
    """
    if not request.json:
        abort(400)

    old = get_price(event_id, role_id)
    if 'price' in request.json:
        old['price'] = request.json['price']

    return jsonify({'price': update_price(old['id'], event_id, role_id,
                                          old['price'])})


@app.route('/v1.0/limits/', methods=['POST', 'GET'])
@cross_origin()
def param_limits():
    """
    Interface for usage with parameters for limits.
    :return:
    """
    event_id = request.args.get('event_id')
    role_id = request.args.get('role_id')

    # Check request method
    if request.method == "GET":

        # Return all limits for event with event_id if role_id doesn't exist,
        # otherwise return one limit based on event_id and role_id
        if role_id is None:
            return jsonify(get_limits(event_id))
        else:
            return jsonify(get_limit(event_id, role_id))
    else:

        # All POST request need authorization
        _jwt_required(app.config['JWT_DEFAULT_REALM'])
        if current_identity is None:
            return unauthorized()
        else:
            mode = request.args.get('mode')

            # Do something based on mode
            if mode is None or mode == "new":

                # Create new limit if everything is provided
                if not request.json or 'size' not in request.json:
                    abort(400)

                if 'role_id' in request.json:
                    role_id = request.json['role_id']

                return jsonify(create_limit(event_id, request.json['size'],
                                            role_id))

            elif mode == "edit" and role_id is not None:

                # Edit existing limit with information provided
                if not request.json:
                    abort(400)

                old = get_limit(event_id, role_id)
                if 'size' in request.json:
                    size = request.json['size']
                else:
                    size = old['size']

                return jsonify(update_limit(old['id'], event_id, role_id,
                                            size))


@app.route('/v1.0/event/<int:event_id>/limits/', methods=['GET'])
def limits(event_id):
    """
    Non-parameter interface for getting limits for event with event_id.
    :param event_id:
    :return:
    """
    return jsonify({'limits': get_limits(event_id)})


@app.route('/v1.0/event/<int:event_id>/role/<int:role_id>/limit/',
           methods=['GET'])
def limit(event_id, role_id):
    """
    Non-parameter interface for getting specific limit
    for event with event_id and role_id.
    :param event_id:
    :param role_id:
    :return:
    """
    return jsonify({'limit': get_limit(event_id, role_id)})


@app.route('/v1.0/event/<int:event_id>/limit/create/', methods=['POST'])
@jwt_required()
def new_limit(event_id):
    """
    Non-parameter interface for creation of new limits.
    :param event_id:
    :return:
    """
    if not request.json or 'size' not in request.json:
        abort(400)

    if 'role_id' not in request.json:
        role_id = None
    else:
        role_id = request.json['role_id']

    return jsonify({'limit': create_limit(event_id, request.json['size'],
                                          role_id)})


@app.route('/v1.0/event/<int:event_id>/role/<int:role_id>/limit/edit/',
           methods=['POST'])
@jwt_required()
def edit_limit(event_id, role_id):
    """
    Non-parameter interface for editing existing limit based
    on event_id and role_id.
    :param event_id:
    :param role_id:
    :return:
    """
    if not request.json:
        abort(400)

    old = get_limit(event_id, role_id)
    if 'size' in request.json:
        size = request.json['size']
    else:
        size = old['size']

    return jsonify({'limit': update_limit(old['id'], event_id, role_id, size)})


@app.route('/v1.0/images/', methods=['GET', 'POST'])
def param_images():
    """
    Interface for usage with parameters for images.
    :return:
    """
    event_id = request.args.get('event_id')

    # Check request method
    if request.method == "GET":

        # If event_id is provided, get image for that event
        if event_id is not None:
            return jsonify(get_image(event_id))
        else:
            abort(400)
    else:

        # All POST request need authorization
        _jwt_required(app.config['JWT_DEFAULT_REALM'])
        if current_identity is None:
            return unauthorized()

        # Image file is needed
        if 'file' not in request.files:
            abort(400)

        # Search for event_id
        if request.json:
            if event_id is None and 'event_id' not in request.json:
                abort(400)
            elif 'event_id' in request.json:
                event_id = request.json['event_id']

        file = request.files['file']

        # Check that file has filename.
        if file.filename == "":
            return jsonify({'Error': "Filename missing"})

        # Check filename's extension
        if file and check_extension(file.filename):

            # Convert filename to secure one
            filename = secure_filename(file.filename)

            # Save file
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            url = config['image_url'] + filename

            return jsonify(add_image(event_id, url))

        abort(400)


if __name__ == '__main__':
    app.run()
