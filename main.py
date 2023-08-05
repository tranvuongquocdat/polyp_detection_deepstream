import sys
import argparse
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst

# Define and parse command-line arguments
parser = argparse.ArgumentParser(description='Process a video using DeepStream.')
parser.add_argument('--input', help='Path to the input video file.', required=True)
parser.add_argument('--output', help='Path to the output video file.', required=True)
parser.add_argument('--config', help='Path to the DeepStream configuration file.', required=True)
args = parser.parse_args()

# Standard GStreamer initialization
GObject.threads_init()
Gst.init(None)

# Create a pipeline
pipeline = Gst.Pipeline()

# Source element for reading from the file
source = Gst.ElementFactory.make("filesrc", "file-source")
source.set_property("location", args.input)

# Decoder element
decoder = Gst.ElementFactory.make("nvv4l2decoder", "decoder")

# Use nvstreammux to create batch of frames from the decoder's outputs
streammux = Gst.ElementFactory.make("nvstreammux", "stream-muxer")

# Set the source pad of the decoder to be the sink pad of the stream muxer
decoder.src_pad.link(streammux.sink_pad)

# Use nvinfer to run inferencing on decoder's outputs
pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
pgie.set_property("config-file-path", args.config)

# Add a nvosd element for drawing bounding boxes, text and region of interest (ROI) polygons
nvosd = Gst.ElementFactory.make("nvdsosd", "on-screen-display")

# Use nvvideoconvert and nvv4l2decoder for converting the NV12 format to RGBA as required by nvosd
nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "video-converter")
nvvidconv2 = Gst.ElementFactory.make("nvvideoconvert", "video-converter2")

# Encoder and codec for writing to the output file
encoder = Gst.ElementFactory.make("nvv4l2h264enc", "h264-encoder")
codec = Gst.ElementFactory.make("h264parse", "h264-parser")

# Container for the output file
container = Gst.ElementFactory.make("qtmux", "mpeg-container")

# Sink element for writing to the file
sink = Gst.ElementFactory.make("filesink", "file-sink")
sink.set_property("location", args.output)

# Add elements to the pipeline
pipeline.add(source)
pipeline.add(decoder)
pipeline.add(streammux)
pipeline.add(pgie)
pipeline.add(nvvidconv)
pipeline.add(nvosd)
pipeline.add(nvvidconv2)
pipeline.add(encoder)
pipeline.add(codec)
pipeline.add(container)
pipeline.add(sink)

# Link the elements together
source.link(decoder)
decoder.link(streammux)
streammux.link(pgie)
pgie.link(nvvidconv)
nvvidconv.link(nvosd)
nvosd.link(nvvidconv2)
nvvidconv2.link(encoder)
encoder.link(codec)
codec.link(container)
container.link(sink)

# Start the pipeline
pipeline.set_state(Gst.State.PLAYING)

# Run until EOS (end of stream)
bus = pipeline.get_bus()
msg = bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS)

# Free resources
pipeline.set_state(Gst.State.NULL)