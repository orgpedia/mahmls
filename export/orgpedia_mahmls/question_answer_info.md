# Metadata for Maharashtra Legislature Question Answer dataset (mahmls)

| Num. | Column           | Type | Description                                 |
|------|------------------|------|---------------------------------------------|
|  1   | title            | str  | Title of the question                       |
|  2   | question_num     | int  | Based on within document numbering.         |
|  3   | long_num         | int  | Question number assigned by Legislature, unique across sessions.|
|  4   | names            | List[str] | Legislators asking the question, '-' separated        | 
|  5   | role             | str  | Role to which the question is asked         |
|  6   | question_date    | date | Date the question was asked.                |
|  7   | question         | str  | Question with all the sub questions         |
|  8   | minister_name    | str  | Name of the minster who answred the question| 
|  9   | answer           | str  | Answer given to the question                |
|  10  | answer_date      | date | Date the question was answered              |
|  11  | house            | str  | Legislature house [Assembly, Council]       |
|  12  | doc_type         | str  | Type of document [Starred, Unstarred]       |
|  13  | session          | str  | Session name [Budget, Monsoon, Winter]      |
|  14  | year             | str  | Year of the sesion                          |
|  15  | url              | str  | URL which has this question                 |
|  16  | name             | str  | Name of the document used internally        |
|  17  | date             | str  | Date of the document, only valid for Starred|
|  18  | list_num         | str  | Global list_num of the document, valid for Unstarred|

