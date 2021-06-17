__author__ = 'Martin Michel <martin@joyofscripting.com>'
__version__ = '0.1.0'

import requests
from pathlib import Path

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


class BlurItTaskStatus(object):
    """Contains information of an anonymization task."""

    def __init__(self, json):
        self.json = json
        self.started = False
        self.succeeded = False
        self.failed = False
        self.result_url = None
        self.error_message = None

        if self.json['status'] == 'Started':
            self.started = True
        elif self.json['status'] == 'Failed':
            self.failed = True
            self.error_message = self.json['error']
        elif self.json['status'] == 'Succeeded':
            self.succeeded = True
            self.result_url = self.json['output_media']
        else:
            error_message = 'Unknown task status: {0}'.format(self.json)
            raise BlurItTaskStatusError(error_message)


class BlurIt(object):
    """Wraps the blurit.io API to blur faces and/or license plates in MP4 videos.

    Args:
        client_id (str): Your client id for the blurit.io API
        secret_id (str): Your secret id for the blurit.io API
    """

    urllogin = 'https://api.services.wassa.io/login'
    urltask = 'https://api.services.wassa.io/innovation-service/anonymization'
    urlresult = 'https://api.services.wassa.io/innovation-service/result/'

    def __init__(self, client_id, secret_id):
        self.client_id = client_id
        self.secret_id = secret_id
        self.token = None
        self._prices_per_mb = {'0-1GB': 0.02, '>1GB': 0.01}
        self._currency = '€'

    def _log_costs(self, path):
        """Logs the estimated costs for the anonymization task.

        Args:
            path (Path): Path to the input file (instance of a Path object from pathlib)
        """
        filesize = path.stat().st_size
        filesize_mb = ((filesize / 1024.0) / 1024.0)

        for range_size, price_per_mb in self._prices_per_mb.items():
            total_price = round((price_per_mb * filesize_mb), 2)
            logger.info('Estimated cost ({0}): {1}{2}'.format(range_size, total_price, self._currency))


    def login(self):
        """Tries to login to the blurit.io API to obtain the bearer token.

        Raises:
            BlurItError: In case an unexpected error occurs
            BlurItAuthError: In case of authentication errors
        """
        logger.info('Trying to login into blurit.io to retrieve bearer token...')

        response = requests.post(BlurIt.urllogin, json={"clientId": self.client_id, "secretId": self.secret_id})
        status_code = response.status_code

        if status_code != 200:
            try:
                content = response.json()
                logger.debug(content)
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
            logger.info('Successfully retrieved bearer token.')
            logger.debug('Bearer token: {0}'.format(self.token))
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
        if not self.token:
            error_message = "No bearer token found. You need to call login() first."
            raise BlurItAuthError(error_message)

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

        if status_code != 200:
            try:
                content = response.json()
                logger.debug(content)
            except ValueError:
                raise BlurItError('Unable to parse response, invalid JSON.')

            if content.get('error') is not None:
                error_message = content['message']
                error_code = content['statusCode']
                error_type = content['error']

                raise BlurItTaskError(error_message, error_type=error_type, error_code=error_code)
            else:
                raise BlurItError('An unknown error occurred.')

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
            BlurItTaskStatusError: In case of task status specific errors
        """
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

        if status_code != 200:
            try:
                content = response.json()
                logger.debug(content)
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
            logger.debug(response.json())
            return BlurItTaskStatus(response.json())
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
            BlurItTaskResultError: In case of task result specific errors
        """
        logger.info('Downloading the blurred video...')
        headers = {
            'accept': '*/*',
            'Authorization': 'Bearer ' + self.token,
        }

        response = requests.get(result_url, headers=headers)
        status_code = response.status_code

        if status_code != 200:
            try:
                content = response.json()
                logger.debug(content)
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