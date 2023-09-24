# Question and Answers from Maharashtra Legislature

This is a data package repository that contains the starred and
unstarred questions asked by legislators in the Mahrashtra Legislature
for the last 10 years. The documents were obtained from the
Maharashtra Legislature Site (http://www.mls.org.in).

The data package also contains the text files of the original marathi
documents published as PDFs on the Maharashtra Legislature Site.

## Data Statistics

| **Num** | **Metric**                     | **Value**   |
| ------- | ------------------------------ | ----------- |
| 1       | Number of documents            |       1,570 |
| 2       | Number of pages                |      74,462 |
| 3       | Number of words                | 2,06,34,643 |
| 4       | Number of question and answers |      82,275 |

## Accessing the data

All the data is available in the [export/orgpedia_mahmls](export/orgpedia_mahmls/) folder and it contains the following directory/files

| **Num** | **File Name**                                                                  | **Description**                                                                                                                                                                                                                             |
| ---------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1          | [Questions/question_answer_mr_2023.csv.gz](export/orgpedia_mahmls/Questions/question_answer_mr_2023.csv.gz) | The list of all the question and answers in Marathi for the year 2023. Also available in JSON format. Gzipped file is 2.5 MB. The Questions directory contains data for all the years from 2014 to 2023                                     |
| 2          | [Questions/question_answer_en_2023.csv.gz](export/orgpedia_mahmls/Questions/question_answer_en_2023.csv.gz) | The list of all the question and answers in English for the year 2023. Also available in JSON format. Gzipped file is 2.5 MB. The Questions directory contains data for all the years from 2014 to 2023                                     |
| 3          | [question_answer.info.md](export/orgpedia_mahmls/question_answer.info.md)                                   | The description of all the columns of the question_answer dataset.                                                                                                                                                                          |
| 4          | [StarredQuestions-docs/2023-Monsoon-Council-StarredQuestions-20230828.mr.txt.gz](export/orgpedia_mahmls/StarredQuestions-docs/StarredQuestions-docs/2023-Monsoon-Council-StarredQuestions-20230828.mr.txt.gz) | The original document containing Starred questions from which the question and answers were extracted in Marathi as a text file. The last field in the file name is the date the Starred questions were discussed on the floor of the house |
| 5          | [UnstarredQuestions/2023-Monsoon-Council-UnstarredQuestions-9.mr.txt.gz](export/orgpedia_mahmls/StarredQuestions-docs/StarredQuestions-docs/2023-Monsoon-Council-UnstarredQuestions-9.mr.txt.gz)         | The original document containing Unstrred questions from which the question and answers were extracted in Marathi as a text file. The last field in the file name is the list number in which the questions is clubbed.                     |
