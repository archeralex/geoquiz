from django.http import HttpResponse
from django.shortcuts import render, redirect

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Country, Quiz, Question

from django.template import RequestContext

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.db.models import Q

#as part of Amazon S3 setup
from django import forms
# part of Amazon S3
from django_boto.s3 import upload

import random
from random import shuffle

#Make a helper function that will verify if someone is logged in or not, and have a parameter that will be the URL to relocate to after they've successfully logged in??

def home(request):
	#return HttpResponse("Home page")
	return render(request, 'geoquiz/home.html', {})

#Would want to return some simple form of error message to the user, so that they know if eg that username is already taken etc
def register(request):
	if request.method != "POST":
		#return HttpResponse("Register page through GET request")
		return render(request, 'geoquiz/register.html', {})

	print request.POST
	#return HttpResponse("Register page through POST request")

	user = User.objects.create_user(first_name = request.POST['first_name'], last_name = request.POST['last_name'], username = request.POST['username'], email = request.POST['email'], password = request.POST['password'])

	if not user:
		return render(request, 'geoquiz/register.html', {})
		#NB I tried doing return redirect('/register/') instead. This still works, but it goes through urls.py then through this whole function again, rather than just going straight to the html page.

	user.save()
	
	#probably would only want to save the country, once know that the entry has been successfully added to auth_user.

	user = authenticate(username=request.POST['username'], password=request.POST['password'])
	login(request,user)

	return redirect('/')
	#check that this works correctly once I have a header showing who's currently logged in.

def login_user(request):
	if request.method != "POST":
		return render(request, 'geoquiz/login.html', {})

	user = authenticate(username=request.POST['username'], password=request.POST['password'])

	if not user:
		#get it to display some kind of temporary pop-up/message or indicator in the HTML now that
		error_message = "Invalid username/password combination"
		return render(request, 'geoquiz/login.html', {"error_message": error_message})

	login(request,user)

	return redirect('/')


def logout_user(request):
	#add in a line to check if someone is actually logged in. If not, just redirect/render home page. Don't want logout message appearing if no logout happened.
	logout(request)

	logout_message = "You've successfully logged out."
	return render(request, 'geoquiz/home.html', {"logout_message": logout_message})

def list(request):
	if not request.user.is_authenticated():
		error_message = "Please log in first"
		return render(request, 'geoquiz/login.html', {'error_message': error_message})

	all_countries = Country.objects.all()

	search = request.GET.get('search')

	if search:
		all_countries = all_countries.filter(Q(name__icontains=search) | Q(capital__icontains=search))

	paginator = Paginator(all_countries,10)

	page = request.GET.get('page')

	try:
		all_countries = paginator.page(page)
	except PageNotAnInteger:
		all_countries = paginator.page(1)
	except EmptyPage:
		all_countries = paginator.page(paginator.num_pages)

	return render(request, 'geoquiz/list.html', {"all_countries": all_countries})

def quiz(request):
	if not request.user.is_authenticated():
		error_message = "Please log in first"
		return render(request, 'geoquiz/login.html', {'error_message': error_message})

	# could do a SQL query to get hold of the different regions, then pass them through as an array. Would allow to do a for loop to print all of the region options
	return render(request, 'geoquiz/quiz.html', {})

def run_quiz(request):
	#need to have something here that redirects person to quiz.html to choose a quiz, if they got to this url directly without doing so... So basically, if not a POST request from quiz.html

	if not request.user.is_authenticated():
		return redirect('/login')

	question_categories = {u'1':'Country to Capital', u'2':'Country to Flag', u'3':'Capital to Country', u'4':'Capital to Flag', u'5':'Flag to Country', u'6':'Flag to Capital'}
	all_question_bases = {u'1':'name', u'2':'name', u'3':'capital', u'4':'capital', u'5':'flag', u'6':'flag'}
	all_answer_bases = {u'1':'capital', u'2':'flag', u'3':'name', u'4':'flag', u'5':'name', u'6':'capital'}


	if request.method == 'POST':	

		submitted_quiz_id = request.POST['quiz_id']

		for key,answer in request.POST.items():
			print 'key', key
			if key != 'SUBMIT' and key !='csrfmiddlewaretoken' and key !='quiz_id' and key!='region' and key!='question_type' and key!='question_base' and key!='answer_base':
				if key == answer:
					corresponding_question = Question.objects.filter(quiz_id=submitted_quiz_id, country_id=key)[0]
					corresponding_question.status=1
					corresponding_question.save()
				else:
					corresponding_question = Question.objects.filter(quiz_id=submitted_quiz_id, country_id=key)[0]
					corresponding_question.status=2
					corresponding_question.save()

		answered_questions = Question.objects.filter(quiz_id=submitted_quiz_id)
		print 'answered_questions', answered_questions
		question_type = request.POST['question_type']
		region = request.POST['region']
		question_base = request.POST['question_base']
		answer_base = request.POST['answer_base']

		# When going from capital to country, don't include countries which don't have a capital in the question list
		if question_base == 'capital':
			countries_in_quiz = Country.objects.filter(region=region).exclude(capital ='NO CAPITAL')
		elif question_base == 'name':
			countries_in_quiz = Country.objects.filter(region=region)

		print '\n'
		print answered_questions[1].country_id
		print '\n'
		user_answered_countries = []
		answered_questions_status = []
		for question in answered_questions:
			country_answer = Country.objects.get(id=request.POST[str(question.country_id)])
			print "country_answer.name", country_answer.name
			user_answered_countries.append(country_answer)
			answered_questions_status.append(question.status)
		print '\nanswered_questions_status\n', answered_questions_status

		return render(request, 'geoquiz/results_quiz.html', {'answered_questions': answered_questions, 'region': region, 'question_type': question_type, 'question_base': question_base, 'answer_base': answer_base, 'countries_in_quiz': countries_in_quiz, 'user_answered_countries':user_answered_countries, 'answered_questions_status':answered_questions_status})



	quiz = Quiz(user_id=request.user.id)
	quiz.save()

	question_type = question_categories[request.GET.get('question_type')]
	question_base = all_question_bases[request.GET.get('question_type')]
	answer_base = all_answer_bases[request.GET.get('question_type')]
	print "\nquestion_base:", question_base
	print "\nanswer_base:", answer_base
	print "\nquestion_type", question_type

	region = request.GET.get('region')

	# When going from capital to country, don't include countries which don't have a capital in the question list
	if question_base == 'capital':
		countries_in_quiz = Country.objects.filter(region=request.GET.get('region')).exclude(capital ='NO CAPITAL')
		countries_in_world = Country.objects.all()
	elif question_base == 'name':
		countries_in_quiz = Country.objects.filter(region=request.GET.get('region'))
		#Only allow countries with a capital to appear as alternative multichoice selections in ALL quiz types
		countries_in_world = Country.objects.all().exclude(capital='NO CAPITAL')
		#still need to add in changing '' to 'NO CAPITAL' for relevant cases in countries_in_quiz

	countries_multichoice = []
	for index,country in enumerate(countries_in_quiz):
		#at the moment, all questions in a quiz will have to be the same type
		question = Question(question_type=request.GET.get('question_type'), status=0, country_id = country.id, quiz_id=quiz.id)
		question.save()

		right_answer = countries_in_quiz[index]
		#adding in the CORRECT answer to this particular question's multichoice options.
		country_multichoice = [right_answer]
		for x in range(0,4):
			wrong_answer = random.choice(countries_in_world)
			while (wrong_answer.id == right_answer.id):
				print "Trigger", wrong_answer.id, right_answer.id
				wrong_answer = random.choice(countries_in_world)
			country_multichoice.append(wrong_answer)
		shuffle(country_multichoice)
		countries_multichoice.append(country_multichoice)

	#to randomise country_in_quiz and countries_multichoice TOGETHER, so as to randomise question order for each quiz
	indices = range(len(countries_in_quiz))
	shuffle(indices)
	#countries_in_quiz_shuffled = [ for x in countries_in_quiz]
	countries_in_quiz_shuffled = []
	countries_multichoice_shuffled = []
	for x in indices:
		countries_in_quiz_shuffled.append(countries_in_quiz[x])
		countries_multichoice_shuffled.append(countries_multichoice[x])


	return render(request, 'geoquiz/run_quiz.html', {'question_type': question_type, 'region':region, 'countries_in_quiz':countries_in_quiz_shuffled, 'countries_multichoice':countries_multichoice_shuffled, 'quiz':quiz, 'question_base': question_base, 'answer_base': answer_base})

#part of Amazon S3
class UploadFileForm(forms.Form):
   #this is the part which causes the 'File:', 'Choose file' button and 'No file chosen' to show up
   file = forms.FileField()

#part of Amazon S3
def upload_file(request):
	if request.method == 'GET' or request.method != 'POST':
		form = UploadFileForm()
		return render(request,'geoquiz/upload_file.html', {'form':form})

	form = UploadFileForm(request.POST, request.FILES)
	if form.is_valid():
		print "request.Files['file']:", request.FILES['file']
		#NB this is the url where the image can be found
		upload_path = upload(request.FILES['file'])
		#upload() derived from django_boto.s3 import upload
	print "upload path:", upload_path

	response = HttpResponse()

	response.write('<h3>File successfully uploaded</h3>')
	response.write('<p>Click <a href="/">here</a> to go back to the home page</p>')

	return response
