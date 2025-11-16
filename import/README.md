Steps to follow to import a new session

1. mkdir websites/mls.org.in/Council/StarredQuestions/PDF2025/monsoon/yadi
2. cd websites/mls.org.in/Council/StarredQuestions/PDF2025/monsoon/yadi
3. wget https://mls.org.in/tarankit-yadi-monsoon-council2025.aspx
4. python ~/orgpedia/mahmls/import/src/download_page_pdf.py -b 'https://mls.org.in/' ./tarankit-yadi-monsoon-council2025.aspx
5. rm important.pdf
6. python ~/orgpedia/mahmls/import/src/create_yaml_from_directory.py $PWD > todo.yml
7. EDIT todo.yml [CHANGE DATE or List NUM and FILE PATH, SESSION]


a. python import/src/create_consolidated_todos.py 
b. python import/src/merge_and_link_from_consolidated.py import/consolidated_todos.json
c. export IA_ACCESS_KEY, IA_SECRET_KEY
d. python import/src/upload_all_to_archive.py import/documents/documents.json import/documents/archive.json import/websites/mls.org.in
