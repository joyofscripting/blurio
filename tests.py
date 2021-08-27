import unittest
import tempfile
from pathlib import Path
import blur_video
import blurio


class BlurVideoTest(unittest.TestCase):

    def test_get_output_filepath(self):
        input_filepath = '/Users/test/test.mp4'
        output_filepath = '/Users/test/test_blurred.mp4'
        self.assertEqual(blur_video.get_output_filepath(input_filepath), output_filepath)

        input_filepath = '/Users/test/test'
        output_filepath = '/Users/test/test_blurred'
        self.assertEqual(blur_video.get_output_filepath(input_filepath), output_filepath)

    def test_input_file_directory(self):
        with tempfile.TemporaryDirectory() as tempdir:
            with self.assertRaises(Exception) as context:
                blur_video.main(['--faces', '--plates', '--input', tempdir])

            self.assertTrue('The given input file does not point to a file' in str(context.exception))

    def test_input_file_does_not_exist(self):
        with self.assertRaises(Exception) as context:
            blur_video.main(['--faces', '--plates', '--input', '12345678987654321'])

        self.assertTrue('The given input file does not exist' in str(context.exception))

    def test_calculate_costs(self):
        with tempfile.NamedTemporaryFile(mode="wb") as video_file:
            video_file.truncate(1024 * 1024)
            video_file_path= Path(video_file.name)
            calculated_costs = blurio.BlurIt.calculate_costs(video_file_path)

            self.assertEqual(calculated_costs['filesize'], 1048576)
            self.assertEqual(calculated_costs['filesize_mb'], 1.0)
            self.assertEqual(calculated_costs['filesize_human_readable'], '1.00MB')

            for cost_item in calculated_costs['costs']:
                if cost_item['range_size'] == '0-1GB':
                    self.assertEqual(cost_item['total_price'], '0.02€')
                elif cost_item['range_size'] == '>1GB':
                    self.assertEqual(cost_item['total_price'], '0.01€')

    def test_blurit_task_no_faces_no_plates(self):
        with self.assertRaises(Exception) as context:
            blurit = blurio.BlurIt('fake_client_id', 'fake_secret_id')
            blurit.logged_in = True
            blurit.start_task('fakefile.mp4', blur_faces=False, blur_plates=False)

        self.assertTrue('You decided not to blur faces and plates in the video. That makes no sense.' in str(context.exception))

if __name__ == '__main__':
    unittest.main()