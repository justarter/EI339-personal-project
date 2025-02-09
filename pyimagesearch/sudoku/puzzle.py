# import the necessary packages
from imutils.perspective import four_point_transform
from skimage.segmentation import clear_border
import numpy as np
import imutils
import cv2

def find_puzzle(image, debug=False):
	# convert the image to grayscale and blur it slightly
	gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)#bgr2gray
	blurred = cv2.GaussianBlur(gray, (7, 7), 3)#ksize width and height(7,7), stdx=stdy=3

	# apply adaptive thresholding and then invert the threshold map
	thresh = cv2.adaptiveThreshold(blurred, 255,#convert to 0 or 255
		cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)#maxvalue=255,blocksize=11,Gaussian weighted sum minus 2
	thresh = cv2.bitwise_not(thresh)# ~1=0,~0=1

	# check to see if we are visualizing each step of the image
	# processing pipeline (in this case, thresholding)
	if debug:
		cv2.imshow("Puzzle Thresh", thresh)
		cv2.waitKey(0)

	# find contours in the thresholded image and sort them by size in
	# descending order
	cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
		cv2.CHAIN_APPROX_SIMPLE)#need 0-1 graph(no gray),only external outline, store only 4 point(one rectangle) for outline
	cnts = imutils.grab_contours(cnts)
	cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

	# initialize a contour that corresponds to the puzzle outline
	puzzleCnt = None

	# loop over the contours
	for c in cnts:
		# approximate the contour
		peri = cv2.arcLength(c, True)#Perimeter
		approx = cv2.approxPolyDP(c, 0.02 * peri, True)#closed contour

		# if our approximated contour has four points, then we can
		# assume we have found the outline of the puzzle
		if len(approx) == 4:
			puzzleCnt = approx
			break

	# if the puzzle contour is empty then our script could not find
	# the outline of the sudoku puzzle so raise an error
	if puzzleCnt is None:
		raise Exception(("Could not find sudoku puzzle outline. "
			"Try debugging your thresholding and contour steps."))

	# check to see if we are visualizing the outline of the detected
	# sudoku puzzle
	if debug:
		# draw the contour of the puzzle on the image and then display
		# it to our screen for visualization/debugging purposes
		output = image.copy()
		cv2.drawContours(output, [puzzleCnt], -1, (0, 255, 0), 2)#thickness 2. green
		cv2.imshow("Puzzle Outline", output)
		cv2.waitKey(0)

	# apply a four point perspective transform to both the original
	# image and grayscale image to obtain a top-down birds eye view
	# of the puzzle
	puzzle = four_point_transform(image, puzzleCnt.reshape(4, 2))
	warped = four_point_transform(gray, puzzleCnt.reshape(4, 2))

	# check to see if we are visualizing the perspective transform
	if debug:
		# show the output warped image (again, for debugging purposes)
		cv2.imshow("Puzzle Transform", puzzle)
		cv2.waitKey(0)

	# return a 2-tuple of puzzle in both RGB and grayscale
	return (puzzle, warped)

def extract_digit(cell, debug=False):
	# apply automatic thresholding to the cell and then clear any
	# connected borders that touch the border of the cell
	h, w = cell.shape

	# original cell
	#if debug:
	#	cv2.imshow("Cell", cell)
	#	cv2.waitKey(0)

	'''#don't use clear_border
	thresh = cv2.threshold(cell, 0, 255,
		cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]#Automatic threshold. >thre,0. <thre,255. index 1 means threshed image
	thresh = clear_border(thresh)
	'''
	blur = cv2.GaussianBlur(cell, (3, 3), 3)
	modified = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 5, 2)
	modified = cv2.bitwise_not(modified)

	k1 = 4
	k2 = 8

	modified[:k1] = 0
	modified[-k1:] = 0
	modified[:, :k1] = 0
	modified[:, -k1:] = 0

	x_weighted = 0
	y_weighted = 0
	for i in range(k2, h - k2):
		for j in range(k2, w - k2):
			x_weighted += i * modified[i, j]
			y_weighted += j * modified[i, j]

	total = np.sum(modified[k2:-k2, k2:-k2])
	x_center = x_weighted / total#算质心
	y_center = y_weighted / total

	rotate = np.array([[1, 0, -y_center + w // 2], [0, 1, -x_center + h // 2]])
	modified = cv2.warpAffine(modified, rotate, (w, h))#move

	# moved cell
	#if debug:
	#	cv2.imshow("Moved Cell", modified)
	#	cv2.waitKey(0)

	# find contours in the thresholded cell
	cnts = cv2.findContours(modified.copy(), cv2.RETR_EXTERNAL,
		cv2.CHAIN_APPROX_SIMPLE)
	cnts = imutils.grab_contours(cnts)

	# if no contours were found than this is an empty cell
	if len(cnts) == 0:
		return None

	# otherwise, find the largest contour in the cell and create a
	# mask for the contour
	c = max(cnts, key=cv2.contourArea)#contour size
	mask = np.zeros(modified.shape, dtype="uint8")
	cv2.drawContours(mask, [c], -1, 255, -1)

	# compute the percentage of masked pixels relative to the total
	# area of the image
	(h, w) = modified.shape
	percentFilled = cv2.countNonZero(mask) / float(w * h)
	#print(percentFilled)

	# if less than 3% of the mask is filled then we are looking at
	# noise and can safely ignore the contour
	if percentFilled < 0.01:
		return None
	'''
	# apply the mask to the thresholded cell
	digit = cv2.bitwise_and(thresh, thresh, mask=mask)#use mask to filter.
	'''

	rotate2 = cv2.getRotationMatrix2D((h // 2, w // 2), 0, 1.5)#放大一点
	digit = cv2.warpAffine(modified, rotate2, (w, h))

	# check to see if we should visualize the masking step
	#if debug:
	#	cv2.imshow("Digit", digit)
	#	cv2.waitKey(0)

	# return the digit to the calling function
	return digit
