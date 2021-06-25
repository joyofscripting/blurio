__author__ = 'Martin Michel <martin@joyofscripting.com>'
__version__ = '0.1.1'

from argparse import ArgumentParser
import time
import sys
from pathlib import Path
import config
import blurio

import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

logger = logging.getLogger(__name__)


def blur_video(filepath, output_filepath, blur_faces, blur_plates):
    """Blurs the faces and/or license plates in a given video mp4 file.

    Args:
        filepath (str): Path to the video file in mp4 format
        output_filepath (str): Path where the blurred version of the video should be saved
        blur_faces (bool): Should the faces in the video be blurred?
        blur_plates (bool): Should the license plates in the video be blurred?
    """
    blurit = blurio.BlurIt(config.client_id, config.secret_id)
    blurit.login()
    job_id = blurit.start_task(filepath, blur_faces=blur_faces, blur_plates=blur_plates)

    while True:
        task_status = blurit.get_task_status(job_id)
        logger.info(task_status)

        if task_status.succeeded or task_status.failed:
            break

        logger.info('Waiting for {0} seconds...'.format(config.check_status_interval))
        time.sleep(config.check_status_interval)

    if task_status.succeeded:
        blurit.get_task_result(task_status.result_url, output_filepath)


def get_output_filepath(filepath):
    """Returns a new output filepath based on a given filepath.
    Given filepath: /Users/max/Desktop/video.mp4
    Returned filepath: /Users/max/Desktop/video_blurred.mp4

    Args:
        filepath (str): Path to an existing file

    Returns:
        str: Path to a not yet existing file
    """
    path = Path(filepath)

    suffix = path.suffix
    filename = path.stem

    counter = 0

    while True:
        if counter == 0:
            new_name = filename + '_blurred' + suffix
        else:
            new_name = filename + '_blurred_' + str(counter) + suffix
        new_path = path.with_name(new_name)
        if not new_path.exists():
            output_filepath = str(new_path)
            break
        counter += 1

    return output_filepath


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-f", "--faces", action="store_true",  help="blur faces in video")
    parser.add_argument("-p", "--plates", action="store_true", help="blur plates in video")
    parser.add_argument("-i", "--input", dest="filepath", required=True, help="input video file in mp4 format")
    args = parser.parse_args()

    path = Path(args.filepath)
    if not path.exists():
        error_message = "The given input file does not exist: {0}".format(args.filepath)
        logger.error(error_message)
        sys.exit()
    elif not path.is_file():
        error_message = "The given input file does not point to a file: {0}".format(args.filepath)
        logger.error(error_message)
        sys.exit()

    if not args.faces and not args.plates:
        error_message = "You decided not to blur faces and plates in the video. That makes no sense."
        logger.error(error_message)
        sys.exit()

    output_filepath = get_output_filepath(args.filepath)
    blur_video(args.filepath, output_filepath, args.faces, args.plates)