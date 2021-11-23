import logging

import numpy as np

import torch
from numpy.core.records import ndarray
from torch import Tensor
# from config import CONFIG["TRACING_ENABLED"]
import cv2
import inspect
import random

from PIL import Image, ImageEnhance

from albumentations import (
    Compose,
    OneOf,
    PadIfNeeded,
    RandomSizedCrop,
    HorizontalFlip,
    VerticalFlip,
    RandomRotate90,
    Transpose,
    GridDistortion,
    CLAHE,
    HueSaturationValue,
)

# from config import configure
#
# CONFIG = configure()

def scale(img, scale, interpolation=cv2.INTER_LINEAR):
    logging.debug(inspect.currentframe().f_code.co_name) # DEBUG # if CONFIG["TRACING_ENABLED"]: logging.debug(inspect.currentframe().f_code.co_name) # DEBUG
    height, width = img.shape[:2]
    new_height, new_width = int(height * scale), int(width * scale)
    img = cv2.resize(img, (new_width, new_height), interpolation=interpolation)
    return img


def imload(filename, gray=False, scale_rate=1.0, enhance=False) -> ndarray:
    logging.debug(inspect.currentframe().f_code.co_name) # DEBUG # if CONFIG["TRACING_ENABLED"]: logging.debug(inspect.currentframe().f_code.co_name) # DEBUG
    # print(filename)
    if not gray:
        image = cv2.imread(filename)  # cv2 read color image as BGR
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # (h, w, 3)
        if scale_rate != 1.0:
            image = scale(image, scale_rate)
        if enhance:
            image = Image.fromarray(np.asarray(image, dtype='uint8'))
            contrast = ImageEnhance.Contrast(image)
            image = contrast.enhance(1.55)
    else:

        image = cv2.imread(filename, -1)  # read gray image
        if scale_rate != 1.0:
            image = scale(image, scale_rate, interpolation=cv2.INTER_NEAREST)
        image = np.asarray(image, dtype='uint8')

    return image


def img_mask_crop(image, mask, size=(256, 256), limits=(224, 512)):
    logging.debug(inspect.currentframe().f_code.co_name) # DEBUG # if CONFIG["TRACING_ENABLED"]: logging.debug(inspect.currentframe().f_code.co_name) # DEBUG
    rc = RandomSizedCrop(height=size[0], width=size[1], min_max_height=limits)
    crops = rc(image=image, mask=mask)
    return crops['image'], crops['mask']


def img_mask_pad(image, mask, target=(288, 288)):
    logging.debug(inspect.currentframe().f_code.co_name) # DEBUG # if CONFIG["TRACING_ENABLED"]: logging.debug(inspect.currentframe().f_code.co_name) # DEBUG
    padding = PadIfNeeded(p=1.0, min_height=target[0], min_width=target[1])
    paded = padding(image=image, mask=mask)
    return paded['image'], paded['mask']


def composed_augmentation(image, mask):
    logging.debug(inspect.currentframe().f_code.co_name) # DEBUG # if CONFIG["TRACING_ENABLED"]: logging.debug(inspect.currentframe().f_code.co_name) # DEBUG
    aug = Compose([
        VerticalFlip(p=0.5),
        HorizontalFlip(p=0.5),
        RandomRotate90(p=0.5),
        HueSaturationValue(hue_shift_limit=20,
                           sat_shift_limit=5,
                           val_shift_limit=15, p=0.5),

        OneOf([
            GridDistortion(p=0.5),
            Transpose(p=0.5)
        ], p=0.5),

        CLAHE(p=0.5)
    ])

    auged = aug(image=image, mask=mask)
    return auged['image'], auged['mask']


def get_random_pos(img, window_shape):
    logging.debug(inspect.currentframe().f_code.co_name) # DEBUG # if CONFIG["TRACING_ENABLED"]: logging.debug(inspect.currentframe().f_code.co_name) # DEBUG
    """ Extract of 2D random patch of shape window_shape in the image """
    w, h = window_shape
    W, H = img.shape[-2:]
    x1 = random.randint(0, W - w - 1)
    x2 = x1 + w
    y1 = random.randint(0, H - h - 1)
    y2 = y1 + h
    return x1, x2, y1, y2


def torch_none(x: Tensor):
    return x


def torch_rot90_(x: Tensor):
    return x.transpose_(2, 3).flip(2)


def torch_rot90(x: Tensor):
    return x.transpose(2, 3).flip(2)


def torch_rot180(x: Tensor):
    return x.flip(2).flip(3)


def torch_rot270(x: Tensor):
    return x.transpose(2, 3).flip(3)


def torch_flipud(x: Tensor):
    return x.flip(2)


def torch_fliplp(x: Tensor):
    return x.flip(3)


def torch_transpose(x: Tensor):
    return x.transpose(2, 3)


def torch_transpose_(x: Tensor):
    return x.transpose_(2, 3)


def torch_transpose2(x: Tensor):
    return x.transpose(3, 2)


def pad_tensor(image_tensor: Tensor, pad_size: int = 32):
    """Pads input tensor to make it's height and width dividable by @pad_size

    :param image_tensor: Input tensor of shape NCHW
    :param pad_size: Pad size
    :return: Tuple of output tensor and pad params. Second argument can be used to reverse pad operation of model output
    """
    rows, cols = image_tensor.size(2), image_tensor.size(3)

    if rows > pad_size:
        pad_rows = rows % pad_size
        pad_rows = pad_size - pad_rows if pad_rows > 0 else 0
    else:
        pad_rows = pad_size - rows

    if cols > pad_size:
        pad_cols = cols % pad_size
        pad_cols = pad_size - pad_cols if pad_cols > 0 else 0
    else:
        pad_cols = pad_size - cols

    if pad_rows == 0 and pad_cols == 0:
        return image_tensor, (0, 0, 0, 0)

    pad_top = pad_rows // 2
    pad_btm = pad_rows - pad_top

    pad_left = pad_cols // 2
    pad_right = pad_cols - pad_left

    pad = [pad_left, pad_right, pad_top, pad_btm]
    image_tensor = torch.nn.functional.pad(image_tensor, pad)
    return image_tensor, pad


def unpad_tensor(image_tensor, pad):
    pad_left, pad_right, pad_top, pad_btm = pad
    rows, cols = image_tensor.size(2), image_tensor.size(3)
    return image_tensor[..., pad_top:rows - pad_btm, pad_left: cols - pad_right]


def image_enhance(img, gama=1.55):
    # image = img
    # if convert:
    image = np.asarray(img * 255, np.uint8)
    # --------- down contrast
    image = Image.fromarray(image)
    # image.show()
    contrast = ImageEnhance.Contrast(image)
    image = contrast.enhance(gama)
    # ----------
    # if convert:
    image = np.asarray(image, np.float32) / 255.0
    return image
