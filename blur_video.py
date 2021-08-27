__author__ = 'Martin Michel <martin@joyofscripting.com>'
__version__ = '0.1.3'

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


def blur_video(filepath, output_filepath, blur_faces, blur_plates, check_status_interval):
    """Blurs the faces and/or license plates in a given video mp4 file.

    Args:
        filepath (str): Path to the video file in mp4 format
        output_filepath (str): Path where the blurred version of the video should be saved
        blur_faces (bool): Should the faces in the video be blurred?
        blur_plates (bool): Should the license plates in the video be blurred?
        check_status_interval (int): How many seconds should be waited before another status check is performed?
    """
    blurit = blurio.BlurIt(config.client_id, config.secret_id)
    blurit.login()
    job_id = blurit.start_task(filepath, blur_faces=blur_faces, blur_plates=blur_plates)

    while True:
        task_status = blurit.get_task_status(job_id)
        logger.info(task_status)

        if task_status.succeeded or task_status.failed:
            break

        logger.info('Waiting for {0} seconds...'.format(check_status_interval))
        time.sleep(check_status_interval)

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


def get_chosen_options(args):
    parser = ArgumentParser()
    parser.add_argument("-f", "--faces", action="store_true", help="blur faces in video")
    parser.add_argument("-p", "--plates", action="store_true", help="blur plates in video")
    parser.add_argument("-c", "--costs", action="store_true", help="calculate costs for processing the video (wo processing the video)")
    parser.add_argument("-i", "--input", dest="filepath", required=True, help="input video file in mp4 format")
    chosen_options = parser.parse_args(args)
    return chosen_options


def main(args):
    chosen_options = get_chosen_options(args)

    path = Path(chosen_options.filepath)
    if not path.exists():
        error_message = "The given input file does not exist: {0}".format(chosen_options.filepath)
        raise FileNotFoundError(error_message)
    elif not path.is_file():
        error_message = "The given input file does not point to a file: {0}".format(chosen_options.filepath)
        raise FileNotFoundError(error_message)

    if chosen_options.costs:
        calculated_costs = blurio.BlurIt.calculate_costs(path)
        logger.info('Video file size: {0}'.format(calculated_costs['filesize_human_readable']))

        for costs_item in calculated_costs['costs']:
            logger.info('Estimated cost ({0}): {1}'.format(costs_item['range_size'], costs_item['total_price']))
    else:
        output_filepath = get_output_filepath(chosen_options.filepath)
        blur_video(chosen_options.filepath, output_filepath, chosen_options.faces, chosen_options.plates, config.check_status_interval)


if __name__ == '__main__':
    args = sys.argv[1:]
    main(args)