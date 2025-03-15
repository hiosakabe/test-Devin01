from django.shortcuts import render, redirect
from django.utils import timezone
from django.urls import reverse
from .models import QuizCategory, QuizQuestion, QuizAnswer, QuizResult
from .forms import PlayerNameForm, QuizAnswerForm

def index(request):
    context = {
        'current_time': timezone.now(),
    }
    return render(request, 'sample_app/index.html', context)

def quiz_start(request):
    if request.method == 'POST':
        form = PlayerNameForm(request.POST)
        if form.is_valid():
            player_name = form.cleaned_data['player_name']
            category = form.cleaned_data['category']
            
            # セッションに情報を保存
            request.session['player_name'] = player_name
            request.session['category_id'] = category.id
            request.session['current_question'] = 0
            request.session['correct_answers'] = 0
            request.session['total_questions'] = 5  # 出題する問題数
            
            return redirect('quiz_question')
    else:
        form = PlayerNameForm()
    
    return render(request, 'sample_app/quiz_start.html', {'form': form})

def quiz_question(request):
    # セッションから情報を取得
    player_name = request.session.get('player_name')
    category_id = request.session.get('category_id')
    current_question = request.session.get('current_question', 0)
    total_questions = request.session.get('total_questions', 5)
    
    if not player_name or current_question >= total_questions:
        return redirect('quiz_result')
    
    # カテゴリーに基づいて問題を取得
    questions = QuizQuestion.objects.filter(category_id=category_id)
    
    if current_question >= questions.count():
        return redirect('quiz_result')
    
    question = questions[current_question]
    
    if request.method == 'POST':
        form = QuizAnswerForm(request.POST, question=question)
        if form.is_valid():
            answer_id = form.cleaned_data['answer']
            answer = QuizAnswer.objects.get(id=answer_id)
            
            if answer.is_correct:
                request.session['correct_answers'] = request.session.get('correct_answers', 0) + 1
            
            request.session['current_question'] = current_question + 1
            return redirect('quiz_question')
    else:
        form = QuizAnswerForm(question=question)
    
    progress = int((current_question / total_questions) * 100)
    
    context = {
        'player_name': player_name,
        'question': question,
        'form': form,
        'current_question': current_question + 1,
        'total_questions': total_questions,
        'progress': progress,
    }
    
    return render(request, 'sample_app/quiz_question.html', context)

def quiz_result(request):
    player_name = request.session.get('player_name')
    category_id = request.session.get('category_id')
    correct_answers = request.session.get('correct_answers', 0)
    total_questions = request.session.get('total_questions', 5)
    
    if not player_name:
        return redirect('quiz_start')
    
    category = QuizCategory.objects.get(id=category_id)
    
    # 結果を保存
    result = QuizResult(
        player_name=player_name,
        score=correct_answers,
    )
    result.save()
    
    # セッションをクリア
    for key in ['player_name', 'category_id', 'current_question', 'correct_answers', 'total_questions']:
        if key in request.session:
            del request.session[key]
    
    context = {
        'player_name': player_name,
        'category': category,
        'correct_answers': correct_answers,
        'total_questions': total_questions,
        'percentage': int((correct_answers / total_questions) * 100),
    }
    
    return render(request, 'sample_app/quiz_result.html', context)
