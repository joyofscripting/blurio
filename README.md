# blurio
blurio is a Python script utilizing the [blurit.io](https://blurit.io)-API to blur faces and/or license plates in MP4 videos.

I often record my bicycle rides with my action cam and post them on [Twitter](https://mobile.twitter.com/applescripter). But manually pixelating faces and license plates in the videos with iMovie is a very tedious and error prone task. So I was glad when I recently found [blurit.io](https://blurit.io) from [Wassa Innovation Services](https://wassa.io/en/).

They offer an [API](https://api.services.wassa.io/doc/) to blur faces and/or license plates in MP4 videos. The service is not free, but the price is very reasonable. So I wrote this Python script which uploads a MP4 video file to their platform, starts an anonymization task and downloads the blurred version of the video once the task is finished.

You can also use their website and frontend to upload your videos and start tasks. But for my workflow it is more convenient to process the files from the command line using their API.

Here is one of my Tweets with a blurred video:
[Tweet with blurred video](https://twitter.com/applescripter/status/1404376063422181382?s=20)

Here is a video with blurred faces and license plates (ca. 304 MB):
[Riding through Berlin-Friedrichshain on a kickbike](http://www.schoolscout24.de/dwnlds/20220330_Rollerfahrt_processed_20220330060850z.mp4)


## Dependencies
In order to use blurio you will need the following software, libraries and modules:

* Python 3.6 or higher
	* [requests](https://pypi.org/project/requests/)
* A valid client and secret id to use the blurit.io-services


## Usage
You can use the blur_video.py script directly from your own command line:

`[MyMacBook:~] martin% python3.6 /Users/martin/PycharmProjects/blurio/blur_video.py --faces --plates --input "/Users/martin/Desktop/sample.mp4"`

The script works with the following arguments:

* --faces : Faces will be blurred in the video
* --plates : License plates will be blurred in the video

(not choosing any of both will result in an error message)

* --costs : The costs for processing the video will be calculated (without actually processing the video)

(you do not need to use the arguments --faces and/or --plates when using --costs)

* --detections: A JSON file containing the positions of the faces blurred in the video will be downloaded additionally

+ --input : Path to the MP4 video file you want to process

The blurred video will be saved at the same location as the source video.

Here is an example:

Source video: `/Users/martin/sample.mp4`

Blurred video: `/Users/martin/sample_blurred.mp4`

Existing files will not be overwritten. Following the above example, if `/Users/martin/sample_blurred.mp4` already exists, the file will be saved to `/Users/martin/sample_blurred_1.mp4`

![](http://www.schoolscout24.de/img/blurio/blurio_terminal.png)

### Configuration
The file named *config.py* contains all settings to adjust blurio to your own environment and special needs:

* client_id : Your blurit.io client id
* secret_id : Your blurit.io secret id
* check\_status\_interval : interval in seconds to check for the current status of an anonymization task

## History

### Version 0.1.4

* some minor bug fixes
* now supports the output_detections_url option to additionally download a JSON file containing the positions of faces blurred in the processed video

### Version 0.1.3

* only minor changes to clean up the code
* added a tests.py file with unit tests

### Version 0.1.2

* new --costs argument, using it will only calculate the video processing costs, but not actually process the video

### Version 0.1.1

* added a method to refresh an expired bearer token
* added methods to check for an expired bearer token
* added a missing task status (sent to server)

### Version 0.1.0

* initial version
