from aenum import Enum, auto
import DixelTools
import os
import logging

class DicomLevel(Enum):
    """
    Enumerated DICOM service levels
    """
    INSTANCES = auto()
    SERIES    = auto()
    STUDIES   = auto()
    PATIENTS  = auto()

    def __str__(self):
        return '{0}'.format(self.name.lower())

    @classmethod
    def abrv(cls, s):
        if type(s) is not DicomLevel:
            s = cls.of(s)
        if s == DicomLevel.INSTANCES:
            return 'i'
        elif s == DicomLevel.SERIES:
            return 'r'
        elif s == DicomLevel.STUDIES:
            return 's'
        elif s == DicomLevel.PATIENTS:
            return 'p'
        logging.warn("Invalid DicomLevel provided {}".format(s))

    @classmethod
    def of(cls, s):
        if s.lower() == "i" or s.lower() == "instances":
            return DicomLevel.INSTANCES
        elif s.lower() == "r" or s.lower() == "series":
            return DicomLevel.SERIES
        elif s.lower() == "s" or s.lower() == "studies":
            return DicomLevel.STUDIES
        elif s.lower() == "p" or s.lower() == "patients":
            return DicomLevel.PATIENTS
        else:
            logging.warn("No defined DicomLevel for {}".format(s))

class Dixel(object):
    """
    An individual DICOM element
    """

    def __init__(self,  id,
                        meta = None,
                        data = None,
                        level = DicomLevel.INSTANCES):

        self.id    = id            # orthanc-type id
        self.meta  = meta or {}    # ParentID, file_uuid, path, ApproxDate, other info
        self.data  = data or {}    # Binary data, pixels, report text
        self.level = level

    def save_archive(self, save_dir):
        if self.data.get('archive'):
            fn = self.meta['PatientID'] + '.zip'
            fp = os.path.join(save_dir, fn)
            with open(fp, 'wb') as f:
                f.write(self.data['archive'])

    @property
    def id0(self):
        if self.meta.get('OID'):
            return self.meta.get('OID')

        if self.level == DicomLevel.STUDIES and \
            self.meta.get('PatientID') and \
            self.meta.get('StudyInstanceUID'):

            self.meta['OID'] = DixelTools.orthanc_id(self.meta.get('PatientID'),
                                                     self.meta.get('StudyInstanceUID'))
            return self.meta.get('OID')

        elif self.level == DicomLevel.SERIES and \
                self.meta.get('PatientID') and \
                self.meta.get('StudyInstanceUID') and \
                self.meta.get('SeriesInstanceUID'):
            self.meta['OID'] = DixelTools.orthanc_id(self.meta.get('PatientID'),
                                                     self.meta.get('StudyInstanceUID'),
                                                     self.meta.get('SeriesInstanceUID'))
            return self.meta.get('OID')

        elif self.level == DicomLevel.INSTANCES and \
                self.meta.get('PatientID') and \
                self.meta.get('StudyInstanceUID') and \
                self.meta.get('SeriesInstanceUID') and \
                self.meta.get('SOPInstanceUID') :
            self.meta['OID'] = DixelTools.orthanc_id(self.meta.get('PatientID'),
                                                     self.meta.get('StudyInstanceUID'),
                                                     self.meta.get('SeriesInstanceUID'),
                                                     self.meta.get('SOPInstanceUID'))
            return self.meta.get('OID')

    # Helpers to make dixels printable, hashable, and sortable for set operations
    def __repr__(self):
        return self.id[0:4]

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __lt__(self, other):
        return self.id < other.id
