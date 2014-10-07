from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.renderers import JSONRenderer, YAMLRenderer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import (ListCreateAPIView, RetrieveUpdateDestroyAPIView, GenericAPIView)
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework import mixins

from django.contrib.auth.hashers import check_password, make_password
from django.http import Http404
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core import serializers as core_serializers

from datetime import date, timedelta

from api import serializers
from xmoney import models
from django.db.models import Sum

@api_view(['POST'])
def Auth(request):
	return 0

class LoggedInRESTAPIView(APIView):
    authentication_classes = ((SessionAuthentication, TokenAuthentication))
    permission_classes = ((IsAuthenticated,))


class LoggedOutRESTAPIView(APIView):
    permission_classes = ((AllowAny,))


class Register(LoggedOutRESTAPIView, GenericAPIView):

    """
    Registers a new Django User object by accepting required field values.

    Accepts the following POST parameters:
        Required: username, password, email
        Optional: first_name & last_name for User object and UserProfile fields
    Returns the newly created User object including REST Framework Token key.
    """

    serializer_class = serializers.UserRegistrationSerializer

    def post(self, request):
        # Create serializers with request.DATA
        serializer = self.serializer_class(data=request.DATA)

        if serializer.is_valid():
            
	    	user = User.objects.create_user(username=request.DATA['username'],  password=request.DATA['password'], email=request.DATA['email'])
	    	user.is_active = True
	    	if request.DATA['first_name']:
	    		user.first_name = request.DATA['first_name']
	    	if request.DATA['last_name']:
	    		user.last_name = request.DATA['last_name']
	    	user.save()	

	    	# create UserProfile
	    	profile = models.Profile.objects.create(user=user, birthday='2000-1-1', sex='', language=models.Profile.CHOICE_LANGUAGE_ENGLISH)

	    	# Return the User object with Created HTTP status
	    	return Response(serializer.data, status=status.HTTP_201_CREATED)

        else:
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)



class UserProfile(LoggedOutRESTAPIView, GenericAPIView):
	"""
	Get Current User Profile Info
	"""
	serializer_class = serializers.UserInfoSerializer

	def get(self, request):
		try:
			user = User.objects.get(pk=request.user.id)
		except:
			return Response(status=404)

		serializer = self.serializer_class(user)
		return Response(serializer.data, status=status.HTTP_200_OK)

	def put(self, request):
		try:
			user = User.objects.get(pk=request.user.id)
		except:
			return Response(status=404)

		serializer = self.serializer_class(user, data=request.DATA)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@login_required
@api_view(['PUT'])
def UserChangePassword(request):
	try:
		user = User.objects.get(pk=request.user.id)
	except:
		return Response(status=404)

	current_password = request.DATA.get('currentpassword', '')
	new_password = request.DATA.get('newpassword', '')
	confirm_password = request.DATA.get('confirmpassword', '')

	if new_password != confirmpassword:
		return Response({'message': 'Please confirm password'})

	elif check_password(current_password, user.password) == False:
		return Response({'message': 'Wrong password'})

	return Response(status=404)

"""
	API get list transactions
	How to use:
		- /api/transaction								get all transaction today
		- /api/transaction?month=current 				get all transaction of this month
		- /api/transaction?month=5						get all transaction of 5th month
		- /api/transaction?month=5&year=2014			get all transaction of 5th month, and year 2014
		- /api/transaction?day=5&month=5&year=2014		get all transaction 5/5/2014
"""

class TransactionOverview(LoggedInRESTAPIView, GenericAPIView):
	serializer_class = serializers.TransactionSerializer

	def post(self, request):
		serializer = self.serializer_class(data=request.DATA)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	def get(self, request):
		today = date.today()
		day 	= request.QUERY_PARAMS.get('day', None)
		month 	= request.QUERY_PARAMS.get('month', today.month)
		year 	= request.QUERY_PARAMS.get('year', today.year)
		limit 	= request.QUERY_PARAMS.get('limit', None)

		if month == 'current':
			month = today.month

		transaction_list = models.Transaction.objects.filter(user=request.user.id, date__year=year, date__month=month)
		if day is not None:
			transaction_list = transaction_list.filter(date__day=day)
		if limit is not None:
			transaction_list = transaction_list[:limit]

		serializer = serializers.TransactionListSerializer(transaction_list, many=True)
		
		return Response(serializer.data)


"""
Show transaction info. 
Add, edit, delete transaction.
"""
class TransactionAction(LoggedInRESTAPIView, GenericAPIView):
	serializer_class = serializers.TransactionSerializer

	def get_object(self, pk):
		try: 
			return models.Transaction.objects.get(pk=pk)
		except models.Transaction.DoesNotExist:
			raise Http404

	def get(self, request, pk):
		serializer = self.serializer_class(self.get_object(pk))
		return Response(serializer.data)
	
	def put(self, request, pk):
		serializer = self.serializer_class(self.get_object(pk), data=request.DATA)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	def delete(self, request, pk):
		Transaction = self.get_object(pk)
		transaction.delete()
		return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def TransactionToday(request):
	today = date.today()
	transactions = models.Transaction.objects.filter(user=request.user.id, date__day=today.day,date__month=today.month, date__year=today.year)

	serializer = serializers.TransactionSerializer(transactions, many=True)
	return Response(serializer.data)	



@api_view(['GET'])
def TransactionMonth(request):
	today = date.today()
	transactions = models.Transaction.objects.filter(user=request.user.id, date__month=today.month, date__year=today.year)

	serializer = serializers.TransactionSerializer(transactions, many=True)
	return Response(serializer.data)


@api_view(['GET'])
def TransactionXMonth(request, month):
	today = date.today()
	transactions = models.Transaction.objects.filter(user=request.user.id, date__month=month, date__year=today.year)

	serializer = serializers.TransactionSerializer(transactions, many=True)
	return Response(serializer.data)



"""
User option of each user
"""
@login_required
@api_view(['GET', 'POST', 'PUT'])
def UserOption(request):
	try:
		user = models.Option.objects.filter(user=request.user.id)
	except:
		return Response(status=404)

	if request.method == 'GET':
		serializer = serializers.UserOptionSerializer(user, many=True)
		return Response(serializer.data)

	if request.method == 'POST':
		serializer = serializers.UserOptionSerializer(user, many=True)
		return Response(serializer.data)		

	if request.method == 'PUT':
		serializer = serializers.UserOptionSerializer(user, many=True)
		return Response(serializer.data)


##############################################################3
########################### CATEGORY #########################3
##############################################################3

class Category(LoggedInRESTAPIView, GenericAPIView):
	serializer_class = serializers.CategorySerializer
	def get(self, request):
		cat = models.Category.objects.all()
		serializer = self.serializer_class(cat, many=True)
		
		return Response(serializer.data)

	def post(self, request):
		if request.DATA['user_id'] != request.user.id:
			return Response({"errors":"You only add category for yourself!"}, status=400)

		serializer = self.serializer_class(data=request.DATA)
		if serializer.is_valid():
			serializer.save() 

			return Response(serializer.data, status=status.HTTP_201_CREATED)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CategoryAction(LoggedInRESTAPIView, GenericAPIView):
	"""
	Get, change or delete transaction provide by <id>
	"""

	serializer_class = serializers.CategorySerializer

	def get_object(self, pk):
		try:
			return models.Category.objects.get(pk=pk)
		except models.Category.DoesNotExist:
			raise Http404

	def get(self, request, pk):
		cat = self.get_object(pk)
		serializer = self.serializer_class(cat)
		return Response(serializer.data, status=status.HTTP_200_OK)

	def put(self, request, pk):
		cat = self.get_object(pk)
		serializer = self.serializer_class(cat, data=request.DATA)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	def delete(self, request, pk):
		cat = self.get_object(pk)
		cat.delete()
		return Response(status=status.HTTP_204_NO_CONTENT)






"""
Notes for user
"""
@api_view(['GET'])
def NoteList(request):
	notes = models.Note.objects.filter(user=request.user.id)
	serializer = serializers.NoteSerializer(notes, many=True)
	return Response(serializer.data)

@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def NoteAction(request, pk):
	try:
		note = models.Note.object.get(user=request.user.id, pk=pk)
	except:
		return Response(status=404)

	if request.method == 'GET':
		serializer = serializers.NoteSerializer(note)
		return Response(serializer.data)

	if request.method == 'POST':
		serializer = serializers.NoteSerializer(data=request.DATA)
		if serializer.is_valid():
			serializer.save()

			return Response(serializer.data, status=status.HTTP_201_CREATED)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	if request.method == 'PUT':
		serializer = serializers.NoteSerializer(note, data=request.DATA)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	if request.method == 'DELETE':
		note.delete()
		return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def DashboardStat(request, type):
	if request.method == 'GET':
		if type == 'all':
			transactions = models.Transaction.objects.filter(user=request.user.id)
		elif type == 'today':
			today = date.today()
			transactions = models.Transaction.objects.filter(user=request.user.id, date__day=today.day,date__year=today.year)
		else:
			return Response(status=400)

		data = {
			'transaction': transactions.count(),
			'income': transactions.filter(transaction_type = models.Transaction.CHOICE_INCOME).aggregate(Sum('value'))['value__sum'],
			'expense': transactions.filter(transaction_type = models.Transaction.CHOICE_EXPENSE).aggregate(Sum('value'))['value__sum']
		}

		serializer = serializers.DashboardStatSerializer(data)
		return Response(serializer.data)


def None2Zero(num):
	return 0 if num is None else num

def group(lst, n):
  for i in range(0, len(lst), n):
    val = lst[i:i+n]
    if len(val) == n:
      yield tuple(val)

def parseStat30Days(stat):
	new_stat = list(group(stat, 5))
	stat = []
	for i in range(0,6):
		stat.append(sum(new_stat[i]))

	return stat

@api_view(['GET'])
def DashboardStatOverview(request):
	if request.method == 'GET':
		type = request.QUERY_PARAMS.get('mode', 'last7day') # last7day, last30day, thisweek, thismonth
		
		if type == 'last7day':
			previous_day = 7
		elif type == 'last30day':
			previous_day = 30
		else:
			return Response(status=500)


		today = date.today()
		num_of_transaction_stat = []
		income_stat = []
		expense_stat = []
		for i in range(0, previous_day):
			t = today - timedelta(days=i)
			transactions = models.Transaction.objects.filter(user=request.user.id, date=t)

			num_of_transaction_stat.append(transactions.count())
			income_stat.append(None2Zero(transactions.filter(transaction_type=models.Transaction.CHOICE_INCOME).aggregate(Sum('value'))['value__sum']))
			expense_stat.append(None2Zero(transactions.filter(transaction_type=models.Transaction.CHOICE_EXPENSE).aggregate(Sum('value'))['value__sum']))


		if type == 'last30day':
			num_of_transaction_stat = parseStat30Days(num_of_transaction_stat)
			income_stat = parseStat30Days(income_stat)
			expense_stat = parseStat30Days(expense_stat)

		data = {
			'num_of_transaction': sum(num_of_transaction_stat),
			'num_of_transaction_stat': reversed(num_of_transaction_stat),

			'income_value': sum(income_stat),
			'income_stat': reversed(income_stat),

			'expense_value': sum(expense_stat),
			'expense_stat': reversed(expense_stat),

			'account': sum(income_stat) - sum(expense_stat),
		}

		serializer = serializers.DashboardStatOverviewSerializer(data)
		return Response(serializer.data)


##############################################################3
########################## WALLET MANAGER ####################3
##############################################################3
class Wallet(LoggedInRESTAPIView, GenericAPIView, mixins.ListModelMixin, mixins.CreateModelMixin):
	serializer_class = serializers.WalletSerializer

	def get(self, request):
		self.queryset = models.Wallet.objects.filter(user=request.user.id)
		return self.list(request)

	def post(self, request, *args, **kwargs):
		return self.create(request, *args, **kwargs)

class WalletAction(LoggedInRESTAPIView, GenericAPIView, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin):
	serializer_class = serializers.WalletSerializer

	def get_object(self, pk):
		try:
			return models.Wallet.objects.get(pk=pk)
		except:
			raise Http404

	def get(self, request, pk):
		serializer = self.serializer_class(self.get_object(pk))
		return Response(serializer.data)

	def put(self, request, pk):
		cat = self.get_object(pk)
		serializer = self.serializer_class(cat, data=request.DATA)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	def delete(self, request, pk):
		cat = self.get_object(pk)
		cat.delete()
		return Response(status=status.HTTP_204_NO_CONTENT)


##############################################################3
########################### AUTO COMPLETE ####################3
##############################################################3

@api_view(['GET'])
def AutoCompleteCategory(request):
	user_id = request.QUERY_PARAMS.get('user_id', request.user.id)
	keyword = request.QUERY_PARAMS.get('keyword', '')

	data = {
		'contents': models.Category.objects.filter(user_id = 0)
	}	#
	#	if keyword != '': 
		#data = data.filter(text__contains=keyword)

	serializer = serializers.AutoCompleteSerializer(data)
	return Response(serializer.data)