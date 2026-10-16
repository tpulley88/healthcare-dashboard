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

# Each condition maps to follow-up note templates. Placeholders are filled by the seed generator.
CONDITION_NOTES = {
    "Hypertension": [
        "BP follow-up. Home readings averaging {sbp}/{dbp}. Tolerating lisinopril without "
        "cough or dizziness. Reinforced low-sodium diet.",
        "Hypertension check. Office BP {sbp}/{dbp}, HR {hr}. No headaches or chest pain. "
        "Continue current antihypertensive regimen.",
    ],
    "Type 2 diabetes": [
        "Diabetes follow-up. A1c {a1c}%. Reviewed glucose log; no hypoglycemic episodes. "
        "Foot exam normal, monofilament sensation intact.",
        "A1c {a1c}%. Discussed carbohydrate counting and activity goals. Continue metformin.",
    ],
    "Asthma": [
        "Asthma check. Using albuterol rescue inhaler {rescue} days per week. Lungs clear, "
        "no wheeze. Peak flow {peak_flow} L/min. Reviewed inhaler technique with spacer.",
        "Mild exacerbation after URI. Expiratory wheeze bilaterally, SpO2 "
        "{spo2_exacerbation}% on room air. Short oral steroid course started; asthma "
        "action plan reviewed.",
    ],
    "COPD": [
        "COPD follow-up. Baseline dyspnea on exertion (mMRC grade 2). SpO2 {spo2_copd}% on "
        "room air at rest. Diminished breath sounds bilaterally, no wheeze. Continues tiotropium "
        "daily; pulmonary rehab referral discussed.",
        "Spirometry: FEV1/FVC {fev1_fvc}, FEV1 {fev1}% predicted. No exacerbations since "
        "last visit. Influenza and pneumococcal vaccines up to date.",
    ],
    "Hyperlipidemia": [
        "Lipid panel reviewed: LDL {ldl} mg/dL. Continue atorvastatin; no myalgias reported.",
    ],
    "Hypothyroidism": [
        "TSH {tsh} mIU/L on current levothyroxine dose. Asymptomatic. No dose change.",
    ],
    "Obstructive sleep apnea": [
        "Sleep apnea follow-up. CPAP download shows use {cpap_hours} hours/night on "
        "{cpap_pct}% of nights, residual AHI {ahi}. Mask fit good, no skin breakdown.",
    ],
    "Atrial fibrillation": [
        "AFib follow-up. Rate controlled, HR {hr} irregularly irregular. Continues "
        "apixaban; no bleeding or bruising reported.",
    ],
    "Osteoarthritis": [
        "Bilateral knee pain, worse with stairs. Mild crepitus, no effusion. Continue "
        "acetaminophen as needed; physical therapy referral placed.",
    ],
    "Generalized anxiety disorder": [
        "Anxiety follow-up. GAD-7 score {gad7}. Sleeping better; continues sertraline and "
        "weekly therapy.",
    ],
}

GENERAL_NOTES = [
    "Annual wellness visit. BP {sbp}/{dbp}, HR {hr}, SpO2 {spo2}% on room air. Age-"
    "appropriate screenings reviewed. No new concerns.",
    "Acute visit for productive cough x {days} days. Afebrile, SpO2 {spo2}% on room air. "
    "Scattered rhonchi clearing with cough. Likely viral bronchitis; supportive care and "
    "return precautions given.",
    "Telephone follow-up on recent lab results. All values within normal limits; patient notified.",
]
