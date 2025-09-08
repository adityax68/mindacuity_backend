-- Seed data for PHQ-9, GAD-7, and PSS-10 tests

-- Insert test definitions
INSERT INTO test_definitions (test_code, test_name, test_category, description, total_questions) VALUES
('phq9', 'PHQ-9', 'depression', 'Patient Health Questionnaire-9: A validated tool for assessing depression severity', 9),
('gad7', 'GAD-7', 'anxiety', 'Generalized Anxiety Disorder-7: A validated tool for assessing anxiety severity', 7),
('pss10', 'PSS-10', 'stress', 'Perceived Stress Scale-10: A validated tool for assessing stress levels', 10);

-- Get test definition IDs
-- PHQ-9 Questions
INSERT INTO test_questions (test_definition_id, question_number, question_text, is_reverse_scored) 
SELECT id, 1, 'Little interest or pleasure in doing things', false FROM test_definitions WHERE test_code = 'phq9'
UNION ALL
SELECT id, 2, 'Feeling down, depressed, or hopeless', false FROM test_definitions WHERE test_code = 'phq9'
UNION ALL
SELECT id, 3, 'Trouble falling or staying asleep, or sleeping too much', false FROM test_definitions WHERE test_code = 'phq9'
UNION ALL
SELECT id, 4, 'Feeling tired or having little energy', false FROM test_definitions WHERE test_code = 'phq9'
UNION ALL
SELECT id, 5, 'Poor appetite or overeating', false FROM test_definitions WHERE test_code = 'phq9'
UNION ALL
SELECT id, 6, 'Feeling bad about yourself - or that you are a failure or have let yourself or your family down', false FROM test_definitions WHERE test_code = 'phq9'
UNION ALL
SELECT id, 7, 'Trouble concentrating on things, such as reading the newspaper or watching television', false FROM test_definitions WHERE test_code = 'phq9'
UNION ALL
SELECT id, 8, 'Moving or speaking slowly enough that other people could have noticed. Or the opposite - being so fidgety or restless that you have been moving around a lot more than usual', false FROM test_definitions WHERE test_code = 'phq9'
UNION ALL
SELECT id, 9, 'Thoughts that you would be better off dead or of hurting yourself in some way', false FROM test_definitions WHERE test_code = 'phq9';

-- GAD-7 Questions
INSERT INTO test_questions (test_definition_id, question_number, question_text, is_reverse_scored) 
SELECT id, 1, 'Feeling nervous, anxious, or on edge', false FROM test_definitions WHERE test_code = 'gad7'
UNION ALL
SELECT id, 2, 'Not being able to stop or control worrying', false FROM test_definitions WHERE test_code = 'gad7'
UNION ALL
SELECT id, 3, 'Worrying too much about different things', false FROM test_definitions WHERE test_code = 'gad7'
UNION ALL
SELECT id, 4, 'Trouble relaxing', false FROM test_definitions WHERE test_code = 'gad7'
UNION ALL
SELECT id, 5, 'Being so restless that it''s hard to sit still', false FROM test_definitions WHERE test_code = 'gad7'
UNION ALL
SELECT id, 6, 'Becoming easily annoyed or irritable', false FROM test_definitions WHERE test_code = 'gad7'
UNION ALL
SELECT id, 7, 'Feeling afraid as if something awful might happen', false FROM test_definitions WHERE test_code = 'gad7';

-- PSS-10 Questions
INSERT INTO test_questions (test_definition_id, question_number, question_text, is_reverse_scored) 
SELECT id, 1, 'In the last month, how often have you been upset because of something that happened unexpectedly?', false FROM test_definitions WHERE test_code = 'pss10'
UNION ALL
SELECT id, 2, 'In the last month, how often have you felt that you were unable to control the important things in your life?', false FROM test_definitions WHERE test_code = 'pss10'
UNION ALL
SELECT id, 3, 'In the last month, how often have you felt nervous and stressed?', false FROM test_definitions WHERE test_code = 'pss10'
UNION ALL
SELECT id, 4, 'In the last month, how often have you felt confident about your ability to handle your personal problems?', true FROM test_definitions WHERE test_code = 'pss10'
UNION ALL
SELECT id, 5, 'In the last month, how often have you felt that things were going your way?', true FROM test_definitions WHERE test_code = 'pss10'
UNION ALL
SELECT id, 6, 'In the last month, how often have you found that you could not cope with all the things that you had to do?', false FROM test_definitions WHERE test_code = 'pss10'
UNION ALL
SELECT id, 7, 'In the last month, how often have you been able to control irritations in your life?', true FROM test_definitions WHERE test_code = 'pss10'
UNION ALL
SELECT id, 8, 'In the last month, how often have you felt that you were on top of things?', true FROM test_definitions WHERE test_code = 'pss10'
UNION ALL
SELECT id, 9, 'In the last month, how often have you been angered because of things that happened that were outside of your control?', false FROM test_definitions WHERE test_code = 'pss10'
UNION ALL
SELECT id, 10, 'In the last month, how often have you felt difficulties were piling up so high that you could not overcome them?', false FROM test_definitions WHERE test_code = 'pss10';

-- Insert response options for PHQ-9 and GAD-7 (same options)
INSERT INTO test_question_options (test_definition_id, question_id, option_text, option_value, weight, display_order)
SELECT 
    td.id,
    tq.id,
    'Not at all',
    0,
    1.0,
    1
FROM test_definitions td
JOIN test_questions tq ON td.id = tq.test_definition_id
WHERE td.test_code IN ('phq9', 'gad7')
UNION ALL
SELECT 
    td.id,
    tq.id,
    'Several days',
    1,
    1.0,
    2
FROM test_definitions td
JOIN test_questions tq ON td.id = tq.test_definition_id
WHERE td.test_code IN ('phq9', 'gad7')
UNION ALL
SELECT 
    td.id,
    tq.id,
    'More than half the days',
    2,
    1.0,
    3
FROM test_definitions td
JOIN test_questions tq ON td.id = tq.test_definition_id
WHERE td.test_code IN ('phq9', 'gad7')
UNION ALL
SELECT 
    td.id,
    tq.id,
    'Nearly every day',
    3,
    1.0,
    4
FROM test_definitions td
JOIN test_questions tq ON td.id = tq.test_definition_id
WHERE td.test_code IN ('phq9', 'gad7');

-- Insert response options for PSS-10
INSERT INTO test_question_options (test_definition_id, question_id, option_text, option_value, weight, display_order)
SELECT 
    td.id,
    tq.id,
    'Never',
    0,
    1.0,
    1
FROM test_definitions td
JOIN test_questions tq ON td.id = tq.test_definition_id
WHERE td.test_code = 'pss10'
UNION ALL
SELECT 
    td.id,
    tq.id,
    'Almost never',
    1,
    1.0,
    2
FROM test_definitions td
JOIN test_questions tq ON td.id = tq.test_definition_id
WHERE td.test_code = 'pss10'
UNION ALL
SELECT 
    td.id,
    tq.id,
    'Sometimes',
    2,
    1.0,
    3
FROM test_definitions td
JOIN test_questions tq ON td.id = tq.test_definition_id
WHERE td.test_code = 'pss10'
UNION ALL
SELECT 
    td.id,
    tq.id,
    'Fairly often',
    3,
    1.0,
    4
FROM test_definitions td
JOIN test_questions tq ON td.id = tq.test_definition_id
WHERE td.test_code = 'pss10'
UNION ALL
SELECT 
    td.id,
    tq.id,
    'Very often',
    4,
    1.0,
    5
FROM test_definitions td
JOIN test_questions tq ON td.id = tq.test_definition_id
WHERE td.test_code = 'pss10';

-- Insert scoring ranges for PHQ-9
INSERT INTO test_scoring_ranges (test_definition_id, min_score, max_score, severity_level, severity_label, interpretation, recommendations, color_code, priority)
SELECT id, 0, 4, 'minimal', 'Minimal Depression', 'No treatment needed', 'Continue monitoring mental health', '#10B981', 1 FROM test_definitions WHERE test_code = 'phq9'
UNION ALL
SELECT id, 5, 9, 'mild', 'Mild Depression', 'Watchful waiting; repeat PHQ-9', 'Consider counseling or therapy', '#F59E0B', 2 FROM test_definitions WHERE test_code = 'phq9'
UNION ALL
SELECT id, 10, 14, 'moderate', 'Moderate Depression', 'Treatment plan, counseling, follow-up', 'Seek professional help', '#EF4444', 3 FROM test_definitions WHERE test_code = 'phq9'
UNION ALL
SELECT id, 15, 19, 'moderately_severe', 'Moderately Severe Depression', 'Active treatment with medication and/or therapy', 'Immediate professional consultation', '#DC2626', 4 FROM test_definitions WHERE test_code = 'phq9'
UNION ALL
SELECT id, 20, 27, 'severe', 'Severe Depression', 'Immediate treatment, medication and therapy', 'Urgent professional intervention', '#991B1B', 5 FROM test_definitions WHERE test_code = 'phq9';

-- Insert scoring ranges for GAD-7
INSERT INTO test_scoring_ranges (test_definition_id, min_score, max_score, severity_level, severity_label, interpretation, recommendations, color_code, priority)
SELECT id, 0, 4, 'minimal', 'Minimal Anxiety', 'No treatment needed', 'Continue monitoring mental health', '#10B981', 1 FROM test_definitions WHERE test_code = 'gad7'
UNION ALL
SELECT id, 5, 9, 'mild', 'Mild Anxiety', 'Watchful waiting; repeat GAD-7', 'Consider stress management techniques', '#F59E0B', 2 FROM test_definitions WHERE test_code = 'gad7'
UNION ALL
SELECT id, 10, 14, 'moderate', 'Moderate Anxiety', 'Treatment plan, counseling, follow-up', 'Seek professional help', '#EF4444', 3 FROM test_definitions WHERE test_code = 'gad7'
UNION ALL
SELECT id, 15, 21, 'severe', 'Severe Anxiety', 'Active treatment with medication and/or therapy', 'Immediate professional consultation', '#DC2626', 4 FROM test_definitions WHERE test_code = 'gad7';

-- Insert scoring ranges for PSS-10
INSERT INTO test_scoring_ranges (test_definition_id, min_score, max_score, severity_level, severity_label, interpretation, recommendations, color_code, priority)
SELECT id, 0, 13, 'low', 'Low Stress', 'Good stress management', 'Continue current stress management practices', '#10B981', 1 FROM test_definitions WHERE test_code = 'pss10'
UNION ALL
SELECT id, 14, 26, 'moderate', 'Moderate Stress', 'Consider stress management techniques', 'Learn and practice stress management techniques', '#F59E0B', 2 FROM test_definitions WHERE test_code = 'pss10'
UNION ALL
SELECT id, 27, 40, 'high', 'High Stress', 'Consider professional help for stress management', 'Seek professional help for stress management', '#EF4444', 3 FROM test_definitions WHERE test_code = 'pss10';
