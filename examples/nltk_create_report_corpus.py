"""
Reads Montage csv output from a source folder, anonymizes and saves
reports into NLTK plaintext corpus format.  Add categories to filenames
to generate a categorized plaintext corpus.

Montage output is segmented into 2 week chunks b/c of the 25k entry
limit on returned items.
"""

from glob import glob
import logging
import os
import csv
from hashlib import md5
import random
from Report import Report
from DixelTools import load_csv, save_csv, orthanc_id

# Set this to the root of your source directory
ROOT_DIR = "/Users/derek/Data/RADCAT"
# A procedure code -> body region mapping
P2BP_LUT = 'img2region.csv'
REBUILD_CORPUS = False
TRIM_AND_UPDATE = True

if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Build a corpus and key
    # source_dir = os.path.join(ROOT_DIR, 'source')
    # out_dir = os.path.join(ROOT_DIR, 'corpus')
    # out_file = os.path.join(ROOT_DIR, "corpus_meta.csv")

    # Create a deidentified reconciliation dataset (with TRIM_AND_UPDATE)
    source_dir = os.path.join(ROOT_DIR, 'reconcile')
    out_file = os.path.join(ROOT_DIR, "reconcile_meta.csv")

    # Setup worklist
    worklist = set()
    fns = glob("{}/*.csv".format(source_dir))

    logging.debug(fns)
    for fn in fns:
        partial, _ = load_csv(fn)

        # For reconcilation -- read radcat from fn and select 100 entries
        if TRIM_AND_UPDATE:
            partial0 = set()
            for d in partial:
                if d.meta['Report Text'].lower().find('swenson') >= 0 or \
                   d.meta['Report Text'].lower().find('movson') >= 0:
                    logging.debug("Throwing out {} report".format(d.meta['Report Finalized By']))
                    continue

                if fn.find('[!-]RADCAT1'):
                    d.meta['radcat'] = 1
                elif fn.find('[!-]RADCAT2'):
                    d.meta['radcat'] = 2
                elif fn.find('[!-]RADCAT4'):
                    d.meta['radcat'] = 4
                elif fn.find('[!-]RADCAT5'):
                    d.meta['radcat'] = 5
                d.meta['radcat3'] = fn.find('[!-]RADCAT3') >= 0
                partial0.add(d)
            partial = random.sample(partial0, 100)

        worklist = worklist.union(partial)

    logging.debug(worklist)

    # Setup procedure -> bodypart lut
    p2bp_lut = {}
    p2bp_lut_fp = os.path.join(ROOT_DIR, P2BP_LUT)
    with open(p2bp_lut_fp, 'r') as f:
        items = csv.DictReader(f)
        for item in items:
            k = item['ProcedureCode']
            v = item['BodyPartName']
            p2bp_lut[k] = v

    for d in worklist:
        r = Report(dixel=d)

        anon_id = orthanc_id(d.meta['PatientID'], d.meta['AccessionNumber'])
        if REBUILD_CORPUS:
            r.write(out_dir, "{}.txt".format(anon_id), anonymize=True, nesting=1)

        age = float( d.meta['Patient Age'] )
        if age <= 18:
            top = round(min(age+2, 18))
            bot = max(1,top-4)
        else:
            bot = round(max(19,age-2))
            top = bot+4
        new_age = random.randint(bot, top)

        if (age > 18 and new_age <= 18) or (age <= 18 and new_age > 18):
            logging.debug('{} age -> {}'.format(age, new_age))

        # test = age > 18 and new_age < 18
        # assert( not test )
        # test = age <= 18 and new_age > 18
        # assert( not test )

        desc = d.meta['Exam Description']
        if desc.startswith("CT"):
            modality = 'CT'
        elif desc.startswith('X-RAY'):
            modality = 'CR'
        elif desc.startswith('US'):
            modality = 'US'
        elif desc.startswith('MR'):
            modality = 'MR'
        elif desc.startswith('PET') or desc.startswith('NM'):
            modality = 'NM'
        elif desc.startswith('DXA'):
            modality = 'DX'
        elif desc.startswith('FL') or desc.startswith('IR'):
            modality = 'FL'
        elif desc.startswith('OUTSIDE STUDY') and desc.find('CT') > 0:
            modality = 'CT'
        elif desc.startswith('OUTSIDE STUDY') and desc.find('CR') > 0:
            modality = 'CR'
        elif desc.startswith('OUTSIDE STUDY') and desc.find('US') > 0:
            modality = 'US'
        else:
            modality = 'UNK'
            logging.warn('Found unknown modality: {}'.format(desc))

        org = d.meta['Organization']
        new_org = md5(org.encode('utf-8')).hexdigest()[0:4]

        physician = d.meta['Report Finalized By']
        new_phys = md5(physician.encode('utf-8')).hexdigest()[0:4]

        code = d.meta['Exam Code']
        body_part = p2bp_lut.get(code, 'Unknown')

        if body_part.lower().find('spine')>0:
            body_part = "Spine"

        if body_part.lower().find('extrem')>0:
            body_part = "Extremity"

        if body_part == "Unknown":
            logging.warn("Found unknown code {}".format(code))

        radcat = d.meta.get('radcat', "UNK")
        if radcat == "UNK":
            logging.warn("No RADCAT in {}".format(d))

        radcat3 = "Yes" if d.meta.get('radcat3') else "No"

        new_meta = {'id': anon_id,
                    'modality': modality,
                    'body_part': body_part,
                    'cpt': d.meta["CPT Code"],
                    'sex': d.meta['Patient Sex'],
                    'age': new_age,
                    'status': d.meta['Patient Status'],
                    'radcat': radcat,
                    'radcat3': radcat3,
                    'radiologist': new_phys,
                    'organization': new_org,
                    'report_text': Report(d.meta['Report Text']).anonymized()
                    }

        d.meta = new_meta

    fieldnames = ['id',
                  'modality',
                  'body_part',
                  'cpt',
                  'sex',
                  'age',
                  'status',
                  'radcat',
                  'radcat3',
                  'radiologist',
                  'organization',
                  'report_text'
                  ]

    save_csv(out_file, worklist, fieldnames)
