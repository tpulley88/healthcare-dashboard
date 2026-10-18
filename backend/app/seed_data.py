"""Synthetic reference data for seeding. No real people, addresses, or records."""

FIRST_NAMES = [
    "Aaliyah", "Adrian", "Aisha", "Alejandro", "Amara", "Andre", "Beatriz", "Benjamin",
    "Camila", "Caleb", "Chen", "Chloe", "Darius", "Diana", "Elena", "Elijah", "Fatima",
    "Gabriel", "Grace", "Hana", "Isaac", "Imani", "Jamal", "Jasmine", "Kenji", "Leah",
    "Luis", "Maya", "Mateo", "Nadia", "Noah", "Olivia", "Omar", "Priya", "Rafael",
    "Rosa", "Samuel", "Sofia", "Thomas", "Yara",
]  # fmt: skip

LAST_NAMES = [
    "Abernathy", "Alvarez", "Bennett", "Brooks", "Castillo", "Chen", "Coleman", "Diaz",
    "Ellison", "Fischer", "Foster", "Garcia", "Hayes", "Ibrahim", "Jensen", "Kim",
    "Kowalski", "Lambert", "Mendoza", "Morales", "Nakamura", "Nguyen", "Okafor", "Olsen",
    "Patel", "Quinn", "Ramirez", "Reyes", "Russo", "Santos", "Schmidt", "Singh",
    "Sullivan", "Tanaka", "Thompson", "Vasquez", "Walsh", "Washington", "Yilmaz", "Zhang",
]  # fmt: skip

STREET_NAMES = [
    "Maple Ave", "Oak St", "Cedar Ln", "Elm St", "Birch Rd", "Willow Way", "Pine St",
    "Harbor View Dr", "Mill Pond Rd", "Chestnut St", "Highland Ave", "Riverside Dr",
]  # fmt: skip

# (city, state, ZIP, area code). Several Northeast ZIPs start with 0, which is why postal
# codes are strings.
LOCATIONS = [
    ("Boston", "MA", "02118", "617"),
    ("Providence", "RI", "02903", "401"),
    ("Hartford", "CT", "06103", "860"),
    ("Newark", "NJ", "07102", "973"),
    ("Burlington", "VT", "05401", "802"),
    ("Portland", "ME", "04101", "207"),
    ("Raleigh", "NC", "27601", "919"),
    ("Columbus", "OH", "43215", "614"),
    ("Denver", "CO", "80202", "303"),
    ("Austin", "TX", "78701", "512"),
    ("Seattle", "WA", "98101", "206"),
    ("Atlanta", "GA", "30303", "404"),
]

# Approximate US distribution.
BLOOD_TYPE_WEIGHTS = {
    "O+": 37, "A+": 36, "B+": 9, "O-": 7, "A-": 6, "AB+": 3, "B-": 1, "AB-": 1,
}  # fmt: skip

ALLERGIES = [
    "Penicillin", "Sulfa drugs", "Latex", "Peanuts", "Shellfish", "Codeine", "Aspirin",
    "Iodinated contrast",
]  # fmt: skip

# Notes follow the SOAP format most outpatient charts use: Subjective, Objective, Assessment,
# Plan, one section per line. The telephone note is free text, as phone encounters usually are.
# Each condition maps to follow-up note templates. Placeholders are filled by the seed generator.
CONDITION_NOTES = {
    "Hypertension": [
        "S: Here for blood pressure follow-up. Home readings averaging {sbp}/{dbp}. "
        "Tolerating lisinopril without cough or dizziness.\n"
        "O: BP {sbp}/{dbp}, HR {hr}. Heart regular, no edema.\n"
        "A: Hypertension, {bp_control}.\n"
        "P: Continue lisinopril 10 mg daily. Reinforced low-sodium diet. Recheck in 3 months.",
        "S: Hypertension check. No headaches, chest pain, or vision changes.\n"
        "O: Office BP {sbp}/{dbp}, HR {hr}. BMP last month: creatinine 0.9, potassium 4.3.\n"
        "A: Hypertension, {bp_control}. Kidney function stable on ACE inhibitor.\n"
        "P: Continue current regimen. Repeat BMP in 6 months.",
    ],
    "Type 2 diabetes": [
        "S: Diabetes follow-up. Checking glucose daily; no hypoglycemic episodes.\n"
        "O: A1c {a1c}%. Foot exam normal, monofilament sensation intact.\n"
        "A: Type 2 diabetes, A1c {a1c}%.\n"
        "P: Continue metformin 1000 mg twice daily. Annual eye exam referral placed.",
        "S: Reviewing A1c result and diet. Struggling with evening snacking.\n"
        "O: A1c {a1c}%, weight stable.\n"
        "A: Type 2 diabetes, glycemic control needs work.\n"
        "P: Discussed carbohydrate counting and activity goals. Continue metformin; "
        "recheck A1c in 3 months.",
    ],
    "Asthma": [
        "S: Asthma check. Using albuterol rescue inhaler {rescue} days per week. "
        "No night waking.\n"
        "O: Lungs clear, no wheeze. Peak flow {peak_flow} L/min.\n"
        "A: Asthma, well controlled.\n"
        "P: Continue current inhalers. Reviewed inhaler technique with spacer.",
        "S: Wheezing and chest tightness for 3 days after a cold.\n"
        "O: Expiratory wheeze bilaterally, SpO2 {spo2_exacerbation}% on room air.\n"
        "A: Mild asthma exacerbation triggered by URI.\n"
        "P: Prednisone 40 mg daily for 5 days. Asthma action plan reviewed. "
        "Return if worsening.",
    ],
    "COPD": [
        "S: COPD follow-up. Baseline dyspnea on exertion, mMRC grade 2. No recent "
        "exacerbations.\n"
        "O: SpO2 {spo2_copd}% on room air at rest. Diminished breath sounds bilaterally, "
        "no wheeze.\n"
        "A: COPD, stable.\n"
        "P: Continue tiotropium daily. Pulmonary rehab referral discussed.",
        "S: Routine COPD review with spirometry. Breathing unchanged.\n"
        "O: FEV1/FVC {fev1_fvc}, FEV1 {fev1}% predicted.\n"
        "A: COPD, moderate airflow obstruction, stable since last visit.\n"
        "P: Continue current inhalers. Influenza and pneumococcal vaccines up to date.",
    ],
    "Hyperlipidemia": [
        "S: Lipid follow-up. No muscle aches on statin.\n"
        "O: LDL {ldl} mg/dL.\n"
        "A: Hyperlipidemia on atorvastatin.\n"
        "P: Continue atorvastatin 20 mg daily. Repeat lipid panel in 1 year.",
    ],
    "Hypothyroidism": [
        "S: Thyroid follow-up. No fatigue, weight change, or cold intolerance.\n"
        "O: TSH {tsh} mIU/L.\n"
        "A: Hypothyroidism, euthyroid on current dose.\n"
        "P: No change to levothyroxine. Recheck TSH in 1 year.",
    ],
    "Obstructive sleep apnea": [
        "S: Sleep apnea follow-up. Feels more rested; mask comfortable.\n"
        "O: CPAP download: {cpap_hours} hours/night on {cpap_pct}% of nights, residual AHI "
        "{ahi}. No skin breakdown.\n"
        "A: Obstructive sleep apnea, adherent to CPAP.\n"
        "P: Continue CPAP at current settings. Follow up in 1 year.",
    ],
    "Atrial fibrillation": [
        "S: AFib follow-up. Occasional palpitations, no dizziness or syncope.\n"
        "O: HR {hr}, irregularly irregular. No bruising.\n"
        "A: Atrial fibrillation, rate controlled, on anticoagulation.\n"
        "P: Continue apixaban 5 mg twice daily and metoprolol. No bleeding reported.",
    ],
    "Osteoarthritis": [
        "S: Bilateral knee pain, worse with stairs.\n"
        "O: Mild crepitus both knees, no effusion, full range of motion.\n"
        "A: Osteoarthritis of both knees.\n"
        "P: Acetaminophen as needed. Physical therapy referral placed.",
    ],
    "Generalized anxiety disorder": [
        "S: Anxiety follow-up. Sleeping better; attending weekly therapy.\n"
        "O: GAD-7 score {gad7}. Calm, good eye contact.\n"
        "A: Generalized anxiety disorder, improving.\n"
        "P: Continue sertraline 50 mg daily and weekly therapy.",
    ],
}

GENERAL_NOTES = [
    "S: Annual wellness visit. No new concerns.\n"
    "O: BP {sbp}/{dbp}, HR {hr}, SpO2 {spo2}% on room air. Exam unremarkable.\n"
    "A: Health maintenance.\n"
    "P: Age-appropriate screenings reviewed and ordered. Return in 1 year.",
    "S: Productive cough for {days} days, no fever or shortness of breath.\n"
    "O: Afebrile, SpO2 {spo2}% on room air. Scattered rhonchi clearing with cough.\n"
    "A: Likely viral bronchitis.\n"
    "P: Supportive care. Return precautions given for fever or shortness of breath.",
    "Telephone follow-up on recent lab results. All values within normal limits; patient notified.",
]
