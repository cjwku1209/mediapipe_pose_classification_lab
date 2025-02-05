import cv2
import tqdm
import numpy as np

from mediapipe.python.solutions import drawing_utils as mp_drawing
from helper.boostrap_helper import BootstrapHelper
from model.pose_embedding import FullBodyPoseEmbedder
from model.pose_classifier import PoseClassifier
from mediapipe.python.solutions import pose as mp_pose
from helper.ema_smoothing import EMADictSmoothing
from helper.classification_visualizer import PoseClassificationVisualizer
from helper.repetition_counter import RepetitionCounter

def preprocessing(bootstrap_images_in_folder, bootstrap_images_out_folder, bootstrap_csvs_out_folder, remove_outliers=False):
    bootstrap_helper = BootstrapHelper(
        bootstrap_images_in_folder, bootstrap_images_out_folder, bootstrap_csvs_out_folder)

    # Check how many pose classes and images for them are available.
    bootstrap_helper.print_images_in_statistics()

    # Bootstrap all images.
    # Set limit to some small number for debug.
    bootstrap_helper.bootstrap(per_pose_class_limit=None)

    # After initial bootstrapping images without detected poses were still saved in
    # the folderd (but not in the CSVs) for debug purpose. Let's remove them.
    bootstrap_helper.align_images_and_csvs(print_removed_items=True)
    bootstrap_helper.print_images_out_statistics()

    # Find outliers.
    # Transforms pose landmarks into embedding.
    pose_embedder = FullBodyPoseEmbedder()

    # Classifies give pose against database of poses.
    pose_classifier = PoseClassifier(
        pose_samples_folder=bootstrap_csvs_out_folder,
        pose_embedder=pose_embedder,
        top_n_by_max_distance=30,
        top_n_by_mean_distance=10)

    outliers = pose_classifier.find_pose_sample_outliers()
    print('Number of outliers: ', len(outliers))

    if (remove_outliers):
        # Remove all outliers (if you don't want to manually pick).
        bootstrap_helper.remove_outliers(outliers)
        # Align CSVs with images after removing outliers.
        bootstrap_helper.align_images_and_csvs(print_removed_items=False)
        bootstrap_helper.print_images_out_statistics()


def run_classification(video_path, class_name, out_video_path):
    video_cap = cv2.VideoCapture(video_path)

    # Get some video parameters to generate output video with classificaiton.
    video_n_frames = video_cap.get(cv2.CAP_PROP_FRAME_COUNT)
    video_fps = video_cap.get(cv2.CAP_PROP_FPS)
    video_width = int(video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Folder with pose class CSVs. That should be the same folder you using while
    # building classifier to output CSVs.
    pose_samples_folder = bootstrap_csvs_out_folder

    # Initialize tracker.
    pose_tracker = mp_pose.Pose()

    # Initialize embedder.
    pose_embedder = FullBodyPoseEmbedder()

    # Initialize classifier.
    # Check that you are using the same parameters as during bootstrapping.
    pose_classifier = PoseClassifier(
        pose_samples_folder=pose_samples_folder,
        pose_embedder=pose_embedder,
        top_n_by_max_distance=30,
        top_n_by_mean_distance=10)

    # Initialize EMA smoothing.
    pose_classification_filter = EMADictSmoothing(
        window_size=10,
        alpha=0.2)

    # Initialize counter.
    repetition_counter = RepetitionCounter(
        class_name=class_name,
        enter_threshold=6,
        exit_threshold=4)

    # Initialize renderer.
    pose_classification_visualizer = PoseClassificationVisualizer(
        class_name=class_name,
        plot_x_max=video_n_frames,
        # Graphic looks nicer if it's the same as `top_n_by_mean_distance`.
        plot_y_max=10)

    # Run classification on a video.

    # Open output video.
    out_video = cv2.VideoWriter(out_video_path, cv2.VideoWriter_fourcc(
        *'mp4v'), video_fps, (video_width, video_height))

    frame_idx = 0
    output_frame = None
    with tqdm.tqdm(total=video_n_frames, position=0, leave=True) as pbar:
        while True:
            # Get next frame of the video.
            success, input_frame = video_cap.read()
            if not success:
                break

            # Run pose tracker.
            input_frame = cv2.cvtColor(input_frame, cv2.COLOR_BGR2RGB)
            result = pose_tracker.process(image=input_frame)
            pose_landmarks = result.pose_landmarks

            # Draw pose prediction.
            output_frame = input_frame.copy()
            if pose_landmarks is not None:
                mp_drawing.draw_landmarks(
                    image=output_frame,
                    landmark_list=pose_landmarks,
                    connections=mp_pose.POSE_CONNECTIONS)

            if pose_landmarks is not None:
                # Get landmarks.
                frame_height, frame_width = output_frame.shape[0], output_frame.shape[1]
                pose_landmarks = np.array([[lmk.x * frame_width, lmk.y * frame_height, lmk.z * frame_width]
                                           for lmk in pose_landmarks.landmark], dtype=np.float32)
                assert pose_landmarks.shape == (
                    33, 3), 'Unexpected landmarks shape: {}'.format(pose_landmarks.shape)

                # Classify the pose on the current frame.
                pose_classification = pose_classifier(pose_landmarks)

                # Smooth classification using EMA.
                pose_classification_filtered = pose_classification_filter(
                    pose_classification)

                # Count repetitions.
                repetitions_count = repetition_counter(
                    pose_classification_filtered)
            else:
                # No pose => no classification on current frame.
                pose_classification = None

                # Still add empty classification to the filter to maintaing correct
                # smoothing for future frames.
                pose_classification_filtered = pose_classification_filter(
                    dict())
                pose_classification_filtered = None

                # Don't update the counter presuming that person is 'frozen'. Just
                # take the latest repetitions count.
                repetitions_count = repetition_counter.n_repeats

            # Draw classification plot and repetition counter.
            output_frame = pose_classification_visualizer(
                frame=output_frame,
                pose_classification=pose_classification,
                pose_classification_filtered=pose_classification_filtered,
                repetitions_count=repetitions_count)

            # Save the output frame.
            out_video.write(cv2.cvtColor(
                np.array(output_frame), cv2.COLOR_RGB2BGR))

            # # Show intermediate frames of the video to track progress.
            # if frame_idx % 50 == 0:
            #     show_image(output_frame)

            frame_idx += 1
            pbar.update()

    # Close output video.
    out_video.release()

    # Release MediaPipe resources.
    pose_tracker.close()


if __name__ == "__main__":
    bootstrap_images_in_folder = './dataset/pushups/pushups_data'
    bootstrap_images_out_folder = './dataset/pushups/dataset_out'
    bootstrap_csvs_out_folder = './dataset/pushups/dataset_csvs'

    # Specify your video name and target pose class to count the repetitions.
    video_path = './dataset/pushups-sample.mp4'
    class_name = 'pushups_down'
    out_video_path = './dataset/pushups-sample-out.mp4'

    preprocessing(bootstrap_images_in_folder,
                  bootstrap_images_out_folder, bootstrap_csvs_out_folder)
    # Run classification on a video.
    run_classification(video_path, class_name, out_video_path)
