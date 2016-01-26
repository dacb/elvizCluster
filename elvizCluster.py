#!/usr/bin/env python
import sys
import numpy as np
import os
import pandas as pd
import re
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from sklearn.cluster import DBSCAN
from sklearn import metrics
from sklearn.datasets.samples_generator import make_blobs
from sklearn.preprocessing import StandardScaler

MIN_ROWS = 20
EPS = 0.15
MIN_SAMPLES = MIN_ROWS

clusterColumns = ['Average fold', 'Reference GC']

sns.set(style="whitegrid")

# read in metadata about samples
meta_info = pd.read_csv("./data/sample_meta_info.tsv", sep="\t")

def readElvizCSV(filename):
    df = pd.read_csv(filename, sep=",", low_memory=False)
    # repalce nans with ""
    df.fillna("", inplace=True)
    return df


def plotClusters(pdf, X, title, labels, core_samples_mask, limits):
    # Black removed and is used for noise instead.
    unique_labels = set(labels)
    colors = plt.cm.Spectral(np.linspace(0, 1, len(unique_labels)), alpha=0.6)
    for k, col in zip(unique_labels, colors):
        if k == -1:
            # black used for noise.
            col = [0, 0, 0, .6]

        class_member_mask = (labels == k)

        xy = X[class_member_mask & core_samples_mask]
        plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=col,
             markeredgecolor='k', markersize=6)

        xy = X[class_member_mask & ~core_samples_mask]
        plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=col,
             markeredgecolor='k', markersize=3)

    plt.title(title)
    plt.xlabel(clusterColumns[0], fontsize=10)
    plt.ylabel(clusterColumns[1], fontsize=10)
    plt.xlim(limits["x"])
    plt.ylim(limits["y"])
    pdf.savefig()
    plt.close()


elvizData = { }
def readElvizCSVs(directory):
    elvizFiles = [filename for filename in os.listdir(directory) if ".csv" in filename]
    for filename in elvizFiles:
        # read the dataframe from the csv
        df = readElvizCSV("./data/" + filename)
        elvizData[filename] = df


def main():
    print("reading in all Elviz CSV files")
    readElvizCSVs("./data/")
    print("concatenating data frames prior to normalization")
    # create a combined dataframe from all the CSV files
    combinedDf = pd.concat(elvizData.values())
    limits = { }
    limits["x"] = [combinedDf['Average fold'].min(), combinedDf['Average fold'].max()]
    limits["x"] = [combinedDf['Average fold'].min(), 500]
    limits["y"] = [combinedDf['Reference GC'].min(), combinedDf['Reference GC'].max()]
    print("normalizing data prior to clustering")
    # normalize the combined data to retrieve the normalization parameters
    scaler = StandardScaler().fit(combinedDf[clusterColumns])
    print("serially processing files")
    for filename in elvizData.keys():
        pdfFilename = filename.replace("csv", "pdf")
        # skip if the PDF already exists
        if os.path.isfile("./results/" + pdfFilename):
            print("skiping file %s" % filename)
            continue
        print("processing file %s" % filename)

        df = elvizData[filename]

        # create a multiage PDF for storing the plots
        with PdfPages('./results/' + pdfFilename) as pdf:
            # find unique values of taxonomy columns
            dfgb = df.groupby(['Kingdom', 'Phylum', 'Class', 'Order', 'Family', 'Genus', 'Species'])
            for key in dfgb.indices.keys():
                idx = dfgb.indices[key]
                taxRows = df.iloc[idx]
                if len(taxRows) < MIN_ROWS:
                    continue
                # normalize all dimensions to be used in clustering, e.g. GC, coverage, rpk
                # reuse the scaler we created from all of the data for the transform
                taxRowsClusterColumns = scaler.transform(taxRows[clusterColumns])

                db = DBSCAN(eps=EPS, min_samples=MIN_SAMPLES).fit(taxRowsClusterColumns)
                core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
                core_samples_mask[db.core_sample_indices_] = True
                labels = db.labels_

                # number of clusters in labels, ignoring noise if present.
                n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)

                if n_clusters_ < 1:
                    continue

                title = ', '.join(key)
                #print(title)
                #print('Estimated number of clusters: %d' % n_clusters_)
                plotClusters(pdf, scaler.inverse_transform(taxRowsClusterColumns), title, labels, core_samples_mask, limits)

        sys.exit()


if __name__ == "__main__":
    main()

