Video Games Industry Analytics Web Application

Simple Flask + SQLite app for an Applied Database Technologies final project.



What it does

* Loads raw `data/my\_vgsales.csv`
* Creates a normalized SQLite database:

  * games
  * platforms
  * genres
  * publishers
  * vg\_sales\_raw
* Displays a filterable game table
* Provides a small summary table
* Supports basic CRUD:

  * create a game
  * update a game
  * delete a game



How to run



python load\_data.py
python app.py


Then open:


http://127.0.0.1:5000/

