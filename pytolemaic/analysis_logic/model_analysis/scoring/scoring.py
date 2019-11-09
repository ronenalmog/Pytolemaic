import numpy
import sklearn
from sklearn.ensemble import RandomForestClassifier

from pytolemaic.utils.constants import CLASSIFICATION, REGRESSION
from pytolemaic.utils.dmd import DMD
from pytolemaic.utils.general import GeneralUtils
from pytolemaic.utils.metrics import Metrics
from pytolemaic.utils.report_keys import ReportScoring
from pytolemaic.utils.report import Report


class Scoring():
    def __init__(self, metrics: list = None):
        self.supported_metric = Metrics.supported_metrics()
        self.metrics = metrics or self.supported_metric
        self.metrics = [self.supported_metric[metric] for metric in
                        self.metrics
                        if metric in self.supported_metric]

    def score_value_report(self, model, dmd_test: DMD,
                           y_proba: numpy.ndarray = None,
                           y_pred: numpy.ndarray = None):
        '''

        :param model: model of interest
        :param dmd_test: test set
        :param y_proba: pre-calculated predicted probabilities for test set, if available
        :param y_pred: pre-calculated models' predictions for test set, if available
        :return: scoring report
        '''
        score_report = {}

        model_support_dmd = GeneralUtils.dmd_supported(model, dmd_test)
        x_test = dmd_test if model_support_dmd else dmd_test.values
        y_true = dmd_test.target

        is_classification = GeneralUtils.is_classification(model)
        if is_classification:

            y_proba = y_proba or model.predict_proba(x_test)
            y_pred = y_pred or numpy.argmax(y_proba, axis=1)

            for metric in self.metrics:
                if not metric.ptype == CLASSIFICATION:
                    continue
                if metric.is_proba:
                    yp = y_proba
                else:
                    yp = y_pred

                score = metric.function(y_true, yp)
                ci_low, ci_high = Metrics.confidence_interval(metric,
                                                              y_true=y_true,
                                                              y_pred=y_pred,
                                                              y_proba=y_proba)
                score_report[metric.name] = {ReportScoring.SCORE_VALUE : score,
                                             ReportScoring.CI_LOW : ci_low,
                                             ReportScoring.CI_HIGH : ci_high}


        else:
            y_pred = y_pred or model.predict(x_test)
            for metric in self.metrics:
                if not metric.ptype == REGRESSION:
                    continue

                score = metric.function(y_true, y_pred)
                ci_low, ci_high = Metrics.confidence_interval(metric,
                                                              y_true=y_true,
                                                              y_pred=y_pred)
                score_report[metric.name] = {ReportScoring.SCORE_VALUE : score,
                                             ReportScoring.CI_LOW : ci_low,
                                             ReportScoring.CI_HIGH : ci_high}


        for metric in score_report:
            score_report[metric] = GeneralUtils.round_values(score_report[metric])

        return Report(score_report)


    def _prepare_dataset_for_score_quality(self, dmd_train: DMD, dmd_test: DMD):
        '''

        :param dmd_train: train set
        :param dmd_test: test set
        :return: dataset with target of test/train
        '''


        dmd = DMD.concat([dmd_train, dmd_test])
        new_label = [0] * dmd_train.n_samples + [1] * dmd_test.n_samples
        dmd.set_target(new_label)

        train, test = dmd.split(ratio=0.5)
        return train, test


    def score_quality_report(self, dmd_train: DMD, dmd_test: DMD):
        '''

        :param dmd_train: train set
        :param dmd_test: test set
        :return: estimation of score quality based on similarity between train and test sets
        '''

        train, test = self._prepare_dataset_for_score_quality(dmd_train=dmd_train,
                                                              dmd_test=dmd_test)

        classifier = RandomForestClassifier(n_estimators=100, n_jobs=10)
        classifier.fit(train.values, train.target.ravel())

        yp = classifier.predict_proba(test.values)

        auc = Metrics.auc.function(y_true=test.target, y_pred=yp)

        return numpy.clip(numpy.round(2*(1-auc), 5),0,1)



if __name__ == '__main__':
    sr = Scoring()
    yt = numpy.random.rand(10)
    d = numpy.random.rand(10)
    print(Metrics.call('mae', yt, yt + 0.1 * d),
          sr._confidence_interval('mae', y_test=yt, y_pred=yt + 0.1 * d))
