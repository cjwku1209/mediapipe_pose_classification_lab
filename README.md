# Pose Classification with MediaPipe

![Funny Cat](https://media.giphy.com/media/JIX9t2j0ZTN9S/giphy.gif)

## Overview

This repository contains code adapted from the [MediaPipe Pose Classification](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/pose_classification.md) solution developed by Google AI Edge. 

## Features

- **Pose Detection**: Uses MediaPipe's pose detection module to extract key points from images.
- **Pose Classification**: Classifies detected poses into predefined categories.
- **Reptition Counter**: Count number of reptition of specific activity like pushups/situps

## Setup

### Prerequisites

Ensure that you have the following installed on your machine:

- Python 3.9
- Matplotlib
- MediaPipe library

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/cjwku1209/mediapipe_pose_classification_lab.git
   cd mediapipe_pose_classification_lab
2. Install python packages:
   ```bash
   pip install pillow==11.0.0
   pip install matplotlib==3.9.2
   pip install numpy==1.26.4
   pip install opencv-python==4.10.0
   pip install tqdm==4.66.5
   pip install mediapipe==0.10.15
3. Download dataset folder [link](https://drive.google.com/file/d/1nj6-rqEfIQ5ZcFOJb_shtLlfb2b6Xe7a/view?usp=sharing)
   - Drag downloaded dataset folder into your cloned repository
  
### Running the Code

```bash
python main.py
```
      
