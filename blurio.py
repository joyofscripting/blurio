__author__ = 'Martin Michel <martin@joyofscripting.com>'
__version__ = '0.1.3'

import requests
from pathlib import Path
from datetime import datetime

import logging
logger = logging.getLogger(__name__)


class BlurItError(Exception):
    def __init__(self, message, error_type=None, error_code=None):
        self.type = error_type

        self.message = message
        if error_type is not None:
            self.message = '%s: %s' % (error_type, message)

        self.code = error_code

        super(BlurItError, self).__init__(self.message)


class BlurItAuthError(BlurItError):
    pass

class BlurItTaskError(BlurItError):
    pass

class BlurItTaskStatusError(BlurItError):
    pass

class BlurItTaskResultError(BlurItError):
    pass

class BlurItOptionsError(BlurItError):
    pass


class BlurItTaskStatus(object):
    """Contains information of an anonymization task."""

    def __init__(self, job_id, json):
        self.job_id = job_id
        self.json = json
        self.sent = False
        self.started = False
        self.succeeded = False
        self.failed = False
        self.result_url = None
        self.error_message = None

        if self.json['status'] == 'Sent':
            self.sent = True
        elif self.json['status'] == 'Started':
            self.started = True
        elif self.json['status'] == 'Failed':
            self.failed = True
            self.error_message = self.json['error']
        elif self.json['status'] == 'Succeeded':
            self.succeeded = True
            self.result_url = self.json['output_media']
        elif self.json['status'] == 'Unknown Job':
            error_message = 'Unknown job id.'.format(self.json)
            raise BlurItTaskStatusError(error_message)
        else:
            error_message = 'Unknown task status: {0}'.format(self.json)
            raise BlurItTaskStatusError(error_message)

    def __repr__(self):
        if self.sent:
            txt = "Status of task for job id {0}: Sent to server".format(self.job_id)
        elif self.started:
            txt = "Status of task for job id {0}: Started".format(self.job_id)
        elif self.succeeded:
            txt = "Status of task for job id {0}: Succeeded".format(self.job_id)
        elif self.failed:
            txt = "Status of task for job id {0}: Failed ({1})".format(self.job_id, self.error_message)
        else:
            txt = "Status of task for job id {0}: Unknown".format(self.job_id)

        return txt



class BlurIt(object):
    """Wraps the blurit.io API to blur faces and/or license plates in MP4 videos.

    Args:
        client_id (str): Your client id for the blurit.io API
        secret_id (str): Your secret id for the blurit.io API
    """

    urllogin = 'https://api.services.wassa.io/login'
    urltoken = 'https://api.services.wassa.io/token'
    urltask = 'https://api.services.wassa.io/innovation-service/anonymization'
    urlresult = 'https://api.services.wassa.io/innovation-service/result/'

    prices_per_mb = {'0-1GB': 0.02, '>1GB': 0.01}
    currency = '€'

    @staticmethod
    def calculate_costs(path):
        """Calculated the estimated costs for the anonymization task.

        Args:
            path (Path): Path to the input file (instance of a Path object from pathlib)

        Returns:
            info_costs (dict): A dictionary with informations about the estimated costs
        """
        calculated_costs = {'filesize': None, 'filesize_mb': None, 'filesize_human_readable': None, 'costs': []}

        filesize = path.stat().st_size
        filesize_mb = ((filesize / 1024.0) / 1024.0)
        filesize_human_readable = BlurIt._human_readable_size(filesize, 2)
        calculated_costs['filesize'] = filesize
        calculated_costs['filesize_mb'] = filesize_mb
        calculated_costs['filesize_human_readable'] = filesize_human_readable

        for range_size, price_per_mb in BlurIt.prices_per_mb.items():
            total_price = '{0}{1}'.format(round((price_per_mb * filesize_mb), 2), BlurIt.currency)
            costs_record = {'range_size': range_size, 'total_price': total_price}
            calculated_costs['costs'].append(costs_record)

        return calculated_costs

    @staticmethod
    def _human_readable_size(size, decimal_places):
        """"Returns a human readable file size.

        Args:
            size (number): File size to be converted into a human readable file size
            decimal_places (int): Number of decimal places that should be displayed

        Returns:
            human_readable_size (str): A human readable file size
        """
        for unit in ['','KB','MB','GB','TB']:
            if size < 1024.0:
                break
            size /= 1024.0
        return f"{size:.{decimal_places}f}{unit}"

    def __init__(self, client_id, secret_id):
        self.client_id = client_id
        self.secret_id = secret_id
        self.token = None
        self.expire_time = None
        self.refresh_token = None
        self.token_creation_date = None
        self.logged_in = False
        self._prices_per_mb = {'0-1GB': 0.02, '>1GB': 0.01}
        self._currency = '€'


    def _log_costs(self, path):
        """Logs the estimated costs for the anonymization task.

        Args:
            path (Path): Path to the input file (instance of a Path object from pathlib)
        """
        calculated_costs = self.calculate_costs(path)
        logger.info('Video file size: {0}'.format(calculated_costs['filesize_human_readable']))

        for costs_item in calculated_costs['costs']:
            logger.info('Estimated cost ({0}): {1}'.format(costs_item['range_size'], costs_item['total_price']))


    def login(self):
        """Tries to login to the blurit.io API to obtain the bearer token.

        Raises:
            BlurItError: In case an unexpected error occurs
            BlurItAuthError: In case of authentication errors
        """
        logger.info('Trying to login into blurit.io to retrieve bearer token...')

        response = requests.post(BlurIt.urllogin, json={"clientId": self.client_id, "secretId": self.secret_id})
        status_code = response.status_code

        logger.debug('Response: {0}'.format(response.content))

        if status_code != 200:
            try:
                content = response.json()
            except ValueError:
                raise BlurItError('Unable to parse response, invalid JSON.')

            if content.get('error') is not None:
                error_message = 'Could not retrieve bearer token.'
                error_code = content['statusCode']
                error_type = content['error']

                raise BlurItAuthError(error_message, error_type=error_type, error_code=error_code)
            else:
                raise BlurItError('An unknown error occurred.')

        try:
            self.token = response.json()['token']
            self.expire_time = response.json()['expireTime']
            self.refresh_token = response.json()['refreshToken']
            self.token_creation_date = datetime.now()
            self.logged_in = True
            logger.info('Successfully retrieved bearer token.')
            logger.debug('Bearer token: {0}'.format(self.token))
        except ValueError:
            raise BlurItError('Unable to parse response, invalid JSON.')
        except AttributeError:
            raise BlurItAuthError('Unable to obtain bearer token.')

    def refresh_expired_token(self):
        """Tries to refresh an expired bearer token.

        Raises:
            BlurItError: In case an unexpected error occurs
            BlurItAuthError: In case of authentication errors
        """
        if not self.logged_in:
            error_message = "No refresh token found. You need to call login() first."
            raise BlurItAuthError(error_message)

        logger.info('Trying to refresh the expired bearer token...')

        headers = {
            'accept': 'application/json',
            'Authorization': 'Bearer ' + self.token
        }

        response = requests.post(BlurIt.urltoken, json={"refreshToken": self.refresh_token}, headers=headers)
        status_code = response.status_code

        logger.debug('Response: {0}'.format(response.content))

        if status_code != 200:
            try:
                content = response.json()
            except ValueError:
                raise BlurItError('Unable to parse response, invalid JSON.')

            if content.get('error') is not None:
                error_message = 'Could not retrieve refreshed bearer token.'
                error_code = content['statusCode']
                error_type = content['error']

                raise BlurItAuthError(error_message, error_type=error_type, error_code=error_code)
            else:
                raise BlurItError('An unknown error occurred.')

        try:
            self.token = response.json()['token']
            self.expire_time = response.json()['expireTime']
            self.refresh_token = response.json()['refreshToken']
            self.token_creation_date = datetime.now()
            self.logged_in = True
            logger.info('Successfully refreshed bearer token.')
            logger.debug('Refreshed bearer token: {0}'.format(self.token))
        except ValueError:
            raise BlurItError('Unable to parse response, invalid JSON.')
        except AttributeError:
            raise BlurItAuthError('Unable to obtain bearer token.')

    def start_task(self, filepath, blur_faces=True, blur_plates=True, included_area=''):
        """Starts an anonymization task to blur the faces and/or license plates in a video.

        Args:
            filepath (str): Path to the video file in mp4 format
            blur_faces (bool): Should the faces in the video be blurred?
            blur_plates (bool): Should the license plates in the video be blurred?
            included_area (str): A rectangular area to precise which area need to be processed, e.g. {"left": 0, "right": 0,5, "top": 0, "bottom": 1}

        Returns:
            anonymization_job_id (str): Job id of the started anonymization task

        Raises:
            BlurItError: In case an unexpected error occurs
            BlurItAuthError: In case of authentication errors
            BlurItTaskError: In case of task specific errors
        """
        if not self.logged_in:
            error_message = "No bearer token found. You need to call login() first."
            raise BlurItAuthError(error_message)

        if not blur_faces and not blur_plates:
            error_message = "You decided not to blur faces and plates in the video. That makes no sense."
            raise BlurItOptionsError(error_message)

        logger.info('Starting anonymization task...')

        input_path = Path(filepath)

        if not input_path.exists():
            error_message = 'The given input file does not exist: {0}'.format(input_path)
            raise BlurItTaskError(error_message)
        elif not input_path.is_file():
            error_message = 'The given input path does not point to a file: {0}'.format(input_path)
            raise BlurItTaskError(error_message)

        filename = input_path.name
        self._log_costs(input_path)

        headers = {
            'accept': 'application/json',
            'Authorization': 'Bearer ' + self.token
        }

        data = {'activation_faces_blur': str(blur_faces).lower(),
                'activation_plates_blur': str(blur_plates).lower(),
                'included_area': included_area
                }

        logger.info('Uploading video file...')

        try:
            with open(filepath, 'rb') as filecont:
                files = {
                    'input_media': (filename, filecont, 'video/mp4')
                }
                response = requests.post(BlurIt.urltask, headers=headers, files=files, data=data)
                status_code = response.status_code
        except IOError as err:
            error_message = 'Could not process given file: {0}'.format(err)
            raise BlurItTaskError(error_message)

        logger.debug('Response: {0}'.format(response.content))

        if status_code != 200:
            try:
                content = response.json()
            except ValueError:
                raise BlurItError('Unable to parse response, invalid JSON.')

            if content.get('error') is not None:
                error_message = content['message']
                error_code = content['statusCode']
                error_type = content['error']

                raise BlurItTaskError(error_message, error_type=error_type, error_code=error_code)
            else:
                raise BlurItError('An unknown error occurred.')

        logger.info('Video file upload finished.')

        try:
            anonymization_job_id = response.json()['anonymization_job_id']
            logger.info('Successfully retrieved job id for anonymization task.')
            logger.debug('Job id: {0}'.format(anonymization_job_id))
            return anonymization_job_id
        except ValueError:
            raise BlurItError('Unable to parse response, invalid JSON.')
        except AttributeError:
            raise BlurItTaskError('Unable to obtain anonymization job id.')

    def get_task_status(self, job_id):
        """Obtains the current status of an anonymization task.

        Args:
            job_id (str): The job id of the anonymization task

        Returns:
            task_status (BlurItTaskStatus): The current status of the anonymization task in question

        Raises:
            BlurItError: In case an unexpected error occurs
            BlurItAuthError: In case of authentication errors
            BlurItTaskStatusError: In case of task status specific errors
        """
        if not self.logged_in:
            error_message = "No bearer token found. You need to call login() first."
            raise BlurItAuthError(error_message)

        logger.info('Getting current status of anonymization task...')

        headers = {
            'accept': 'application/json',
            'Authorization': 'Bearer ' + self.token,
        }

        params = (
            ('anonymization_job_id', job_id),
        )

        response = requests.get(BlurIt.urltask, headers=headers, params=params)
        status_code = response.status_code

        logger.debug('Response: {0}'.format(response.content))

        if status_code != 200:
            try:
                content = response.json()
            except ValueError:
                raise BlurItError('Unable to parse response, invalid JSON.')

            if content.get('error') is not None:
                error_message = content['message']
                error_code = content['statusCode']
                error_type = content['error']

                raise BlurItTaskStatusError(error_message, error_type=error_type, error_code=error_code)
            else:
                raise BlurItError('An unknown error occurred.')

        try:
            logger.info('Successfully retrieved the current status.')
            return BlurItTaskStatus(job_id, response.json())
        except ValueError:
            raise BlurItError('Unable to parse response, invalid JSON.')
        except AttributeError:
            raise BlurItTaskStatusError('Unable to obtain anonymization job id.')

    def get_task_result(self, result_url, filepath):
        """Downloads the result of an anonymization task to a local file.

        Args:
            result_url (str): The url where the blurred result can be downloaded
            filepath (str): Path to the file where the blurred video should be saved

        Raises:
            BlurItError: In case an unexpected error occurs
            BlurItAuthError: In case of authentication errors
            BlurItTaskResultError: In case of task result specific errors
        """
        if not self.logged_in:
            error_message = "No bearer token found. You need to call login() first."
            raise BlurItAuthError(error_message)

        logger.info('Downloading the blurred video...')
        headers = {
            'accept': '*/*',
            'Authorization': 'Bearer ' + self.token,
        }

        response = requests.get(result_url, headers=headers)
        status_code = response.status_code

        #logger.debug('Response: {0}'.format(response.content))

        if status_code != 200:
            try:
                content = response.json()
            except ValueError:
                raise BlurItError('Unable to parse response, invalid JSON.')

            if content.get('error') is not None:
                error_message = content['message']
                error_code = content['statusCode']
                error_type = content['error']

                raise BlurItTaskResultError(error_message, error_type=error_type, error_code=error_code)
            else:
                raise BlurItError('An unknown error occurred.')

        try:
            with open(filepath, 'wb') as filecont:
                for chunk in response.iter_content(chunk_size=255):
                    if chunk:
                        filecont.write(chunk)
            logger.info('Successfully downloaded the blurred video to {0}.'.format(filepath))
        except IOError as err:
            error_message = 'Could not save file: {0}'.format(err)
            raise BlurItTaskResultError(error_message)

    def token_seconds_left(self):
        """Returns the seconds left before the bearer token will expire.

        Returns:
            seconds_left (int): seconds left before the bearer token will expire

        Raises:
            BlurItAuthError: In case of authentication errors
        """
        if not self.logged_in:
            error_message = "No bearer token found. You need to call login() first."
            raise BlurItAuthError(error_message)

        now = datetime.now()
        difference = (now - self.token_creation_date)
        diff_seconds = difference.total_seconds()

        seconds_left = int(self.expire_time - diff_seconds)

        if seconds_left < 0:
            return 0
        else:
            return seconds_left

    def token_is_expired(self):
        """Indicates if the bearer token is expired or not.

        Returns:
            is_expired (boolean): Boolean flag indicating whether the bearer token is expired or not

        Raises:
            BlurItAuthError: In case of authentication errors
        """
        seconds_left = self.token_seconds_left()
        if seconds_left == 0:
            return True
        else:
            return False