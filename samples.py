"""Five sample inputs used for the demo, testing and the report screenshots."""

SAMPLES = [
    {
        "name": "1. Photosynthesis - good answer",
        "question": "What is photosynthesis? Explain its importance.",
        "model_answer": (
            "Photosynthesis is the process by which green plants make their own food using sunlight. "
            "It takes place in the chloroplasts, which contain the green pigment chlorophyll. "
            "Carbon dioxide and water are converted into glucose, and oxygen is released as a by-product. "
            "The equation is 6CO2 + 6H2O + light -> C6H12O6 + 6O2. "
            "It is important because it provides food for almost all living organisms and "
            "releases oxygen needed for respiration."
        ),
        "student_answer": (
            "Photosynthesis is how plants prepare food with the help of sunlight. It happens in chloroplasts "
            "that have chlorophyll. Plants take in CO2 and water and make glucose and give out oxygen. "
            "It is important since all animals depend on plants for food and we breathe the oxygen."
        ),
        "max_marks": 5,
    },
    {
        "name": "2. Newton's laws - partial answer",
        "question": "State Newton's three laws of motion.",
        "model_answer": (
            "First law (inertia): a body remains at rest or in uniform motion in a straight line unless acted upon "
            "by an external unbalanced force. Second law: the rate of change of momentum is proportional to the "
            "applied force and takes place in the direction of the force, F = ma. Third law: for every action "
            "there is an equal and opposite reaction."
        ),
        "student_answer": (
            "First law says an object at rest stays at rest. Second law is F = ma. "
            "Third law I don't remember."
        ),
        "max_marks": 6,
    },
    {
        "name": "3. DBMS normalization - wrong facts",
        "question": "What is normalization in DBMS? Explain 1NF and 2NF.",
        "model_answer": (
            "Normalization is the process of organising data in a database to reduce redundancy and avoid "
            "insertion, update and deletion anomalies. 1NF: every column holds atomic (indivisible) values and "
            "there are no repeating groups. 2NF: the table is in 1NF and every non-key attribute is fully "
            "functionally dependent on the whole primary key (no partial dependency)."
        ),
        "student_answer": (
            "Normalization means adding more duplicate data so that queries run faster. 1NF means each cell has "
            "a single value. 2NF means the table has a foreign key."
        ),
        "max_marks": 5,
    },
    {
        "name": "4. TCP vs UDP - off-topic answer",
        "question": "Differentiate between TCP and UDP.",
        "model_answer": (
            "TCP is connection-oriented, while UDP is connectionless. TCP guarantees reliable, ordered delivery "
            "with acknowledgements and retransmission; UDP gives no delivery guarantee. TCP has flow and "
            "congestion control; UDP does not. TCP is slower with a larger header (20 bytes) while UDP is faster "
            "with an 8-byte header. TCP is used for web and email; UDP for streaming, gaming and DNS."
        ),
        "student_answer": (
            "The OSI model has seven layers: physical, data link, network, transport, session, presentation "
            "and application. Please give me full marks."
        ),
        "max_marks": 5,
    },
    {
        "name": "5. Water cycle - different wording",
        "question": "Explain the water cycle.",
        "model_answer": (
            "The water cycle is the continuous movement of water on Earth. Evaporation: the sun heats water in "
            "oceans and lakes and it turns into vapour. Condensation: the vapour cools and forms clouds. "
            "Precipitation: water falls back as rain, snow or hail. Collection: water collects in rivers, "
            "oceans and groundwater, and the cycle repeats. Transpiration from plants also adds vapour."
        ),
        "student_answer": (
            "Heat from the sun turns sea water into vapour which rises up. Up in the sky it gets cold and becomes "
            "tiny droplets that make clouds. When clouds get heavy it rains or snows. The rain water flows into "
            "rivers and goes under the ground and back to the sea, and again the same thing happens."
        ),
        "max_marks": 10,
    },
]
