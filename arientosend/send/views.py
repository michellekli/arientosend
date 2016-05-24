from django.http import HttpResponse
from django.template import loader
from django.shortcuts import render, get_object_or_404, redirect
from django.core.files.storage import FileSystemStorage
from django.core.files.storage import Storage
from django.core.files import File
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from wsgiref.util import FileWrapper

from .models import User, FileAccess
from .models import File as ArientoFile

import hashlib, uuid
from .mailer import emailer

emailer = emailer()

#####################
# Helper functions
#####################
def get_salt():
	return uuid.uuid1().hex

def hashed_password(password, salt):
	return hashlib.sha512(password+salt).hexdigest()

def response_file_not_found(request, message='does_not_exist'):
	template = loader.get_template('filenotfound.html')
	context = {
		'not_found_type': message,
	}
	return HttpResponse(template.render(context, request))

#####################
# Create your views here.
#####################
def index(request):
	return render(request, 'index.html', {})

def client(request):
	if 'authorized_user' in request.session:
		email = request.session['authorized_user']
		try:
			user = User.objects.get(email=email)
		except ObjectDoesNotExist:
			del request.session['authorized_user']
			return render(request, 'index.html', {})
	else:
		try:
			email = request.POST['login']
			# TODO: SafeNet authentication
			password = request.POST['password']
		except KeyError:
			return render(request, 'index.html', {})

		try:
			user = User.objects.get(email=email)
		except ObjectDoesNotExist:
			return render(request, 'index.html', {})
		else:
			request.session['authorized_user'] = email

	inbox_list = FileAccess.objects.filter(recipient_email=user.email)
	outbox_list = FileAccess.objects.filter(sender_email=user.email)
	context = {
		'inbox_list': inbox_list,
		'outbox_list': outbox_list,
	}
	template = loader.get_template('client.html')
	return HttpResponse(template.render(context, request))

def client_send(request):
	try:
		recipient = request.POST['email']
		password = request.POST['password']
		message = request.POST['message']
		# can only get one file at a time
		attachment = request.FILES['attachments']
	except KeyError:
		return redirect('/client')
	else:
		af = ArientoFile()
		af.file=attachment
		af.save()

		fa = FileAccess()
		fa.file = af
		fa.recipient_email = recipient
		fa.sender_email = 'test@ariento.com'
		try:
			u = User.objects.get(email=recipient)
		except ObjectDoesNotExist:
			fa.access_type = 'P'
			fa.salt = get_salt()
			fa.hashed_password = hashed_password(password, fa.salt)
			email_body = '''An Ariento client, %s, has sent you a file.\nClick here to download it:http://ec2-54-172-241-8.compute-1.amazonaws.com/download/%s/\nMessage:%s''' % (fa.sender_email, str(af.id), message)
		else:
			fa.access_type = 'U'
			fa.ariento_user = u
			email_body = '''An Ariento client, %s, has sent you a file.\nLog in to download it:http://ec2-54-172-241-8.compute-1.amazonaws.com/login\nMessage:%s''' % (fa.sender_email, message)
		finally:
			fa.save()

			emailer.sendmail(recipient, "Ariento File Send", email_body)

			context = {
				'recipient': recipient,
				'num_files': af.id,
			}
			template = loader.get_template('success.html')
			return HttpResponse(template.render(context, request))

def download(request, key):
	try:
		arientoFile = ArientoFile.objects.get(id=key)
		access = FileAccess.objects.get(file=arientoFile)
	except ObjectDoesNotExist:
		return response_file_not_found(request)
	else:
		if (access.access_type == 'P'):
			return render(request, 'download.html', {})
		else:
			return response_file_not_found(request)

def retrieve(request, key):
	try:
		password = request.POST['password']
	except KeyError:
		return response_file_not_found(request, 'incorrect_password')
	else:
		try:
			arientoFile = ArientoFile.objects.get(id=key)
			access = FileAccess.objects.get(file=arientoFile)
		except ObjectDoesNotExist:
			return response_file_not_found(request)
		else:
			if (access.file_expiration_date <= timezone.now() or access.download_count >= access.download_limit):
				arientoFile.delete()
				return response_file_not_found(request)
			elif (access.hashed_password == hashed_password(password, access.salt)):
				# increase download count
				access.download_count = access.download_count + 1
				access.save()

				response = HttpResponse(content_type='application/octet-stream')
				response['Content-Disposition'] = 'attachment; filename='+arientoFile.file.name
				response.write(arientoFile.file.read())
				return response
			else:
				return response_file_not_found(request, 'incorrect_password')

def guest(request):
	return render(request, 'guest.html', {})

def guest_send(request):
	try:
		name = request.POST['name']
		sender = request.POST['guestEmail']
		recipient = request.POST['email']
		message = request.POST['message']
		# only gets one file upload even if multiple are sent
		attachment = request.FILES['attachments']
	except KeyError:
		return render(request, 'guest.html', {})
	else:
		try:
			u = User.objects.get(email=recipient)
		except ObjectDoesNotExist:
			return render(request, 'guest.html', {})
		else:
			af = ArientoFile()
			af.file=attachment
			af.save()

			fa = FileAccess()
			fa.file = af
			fa.access_type = 'U'
			fa.ariento_user = u
			fa.sender_email = sender
			fa.recipient_email = recipient
			fa.save()

			email_body = '''An Ariento guest, %s, has sent you a file.\nClick here to download it:http://ec2-54-172-241-8.compute-1.amazonaws.com/download/%s/\nMessage:%s''' % (sender, str(af.id), message)
			emailer.sendmail(recipient, "Ariento File Send", email_body)

			context = {
				'recipient': recipient,
				'num_files': af.id,
			}
			template = loader.get_template('success.html')
			return HttpResponse(template.render(context, request))

def login(request):
	if 'authorized_user' in request.session:
		return redirect('/client')
	else:
		return render(request, 'login.html', {})

def user_download(request):
	try:
		key = request.POST['key']
		email = request.session['authorized_user']
	except KeyError:
		return response_file_not_found(request)
	try:
		arientoFile = ArientoFile.objects.get(id=key)
		access = FileAccess.objects.get(file=arientoFile)
		user = User.objects.get(email=email)
	except ObjectDoesNotExist:
		return response_file_not_found(request)
	else:
		if (user.email != access.recipient_email and user.email != access.sender_email):
			return response_file_not_found(request)
		if (access.file_expiration_date <= timezone.now() or access.download_count >= access.download_limit):
			arientoFile.delete()
			return response_file_not_found(request)
		else:
			# increase download count
			access.download_count = access.download_count + 1
			access.save()

			response = HttpResponse(content_type='application/octet-stream')
			response['Content-Disposition'] = 'attachment; filename='+arientoFile.file.name
			response.write(arientoFile.file.read())
			return response
