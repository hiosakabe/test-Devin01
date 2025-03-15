from django.shortcuts import render, redirect
from django.utils import timezone
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import QuizCategory, QuizQuestion, QuizAnswer, QuizResult, QuizSession, QuizParticipant
from .forms import PlayerNameForm, QuizAnswerForm, QuizSessionForm, JoinSessionForm
import json

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

def quiz_host(request):
    """クイズマスターのホスト画面"""
    if request.method == 'POST':
        form = QuizSessionForm(request.POST)
        if form.is_valid():
            quiz_master = form.cleaned_data['quiz_master']
            category = form.cleaned_data['category']
            total_questions = form.cleaned_data['total_questions']
            
            # セッションを作成
            session = QuizSession(
                quiz_master=quiz_master,
                category=category,
                total_questions=total_questions
            )
            session.save()
            
            return redirect('quiz_session', session_id=session.session_id)
    else:
        form = QuizSessionForm()
    
    return render(request, 'sample_app/quiz_host.html', {'form': form})

def quiz_join(request):
    """参加者のセッション参加画面"""
    if request.method == 'POST':
        form = JoinSessionForm(request.POST)
        if form.is_valid():
            session_id = form.cleaned_data['session_id']
            player_name = form.cleaned_data['player_name']
            
            try:
                session = QuizSession.objects.get(session_id=session_id)
                
                # 参加者を追加
                participant = QuizParticipant(
                    session=session,
                    name=player_name
                )
                participant.save()
                
                return redirect('quiz_session', session_id=session.session_id)
            except QuizSession.DoesNotExist:
                form.add_error('session_id', '指定されたセッションIDは存在しません。')
    else:
        form = JoinSessionForm()
    
    return render(request, 'sample_app/quiz_join.html', {'form': form})

def quiz_session(request, session_id):
    """クイズセッション画面"""
    try:
        session = QuizSession.objects.get(session_id=session_id)
        participants = session.participants.all()
        
        # クイズマスターかどうかを判定
        is_quiz_master = request.GET.get('name') == session.quiz_master
        
        context = {
            'session': session,
            'participants': participants,
            'is_quiz_master': is_quiz_master,
        }
        
        return render(request, 'sample_app/quiz_session.html', context)
    except QuizSession.DoesNotExist:
        return redirect('index')

@csrf_exempt
def quiz_api(request, session_id):
    """クイズAPIエンドポイント"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            session = QuizSession.objects.get(session_id=session_id)
            
            if action == 'get_question':
                question_index = data.get('question_index')
                questions = QuizQuestion.objects.filter(category=session.category)
                
                if question_index < questions.count():
                    question = questions[question_index]
                    answers = question.answers.all()
                    
                    return JsonResponse({
                        'id': question.id,
                        'text': question.question_text,
                        'answers': [{'id': answer.id, 'text': answer.answer_text} for answer in answers]
                    })
                else:
                    return JsonResponse({'error': '質問が見つかりません。'}, status=404)
            
            elif action == 'submit_answer':
                participant_name = data.get('name')
                answer_id = data.get('answer_id')
                
                answer = QuizAnswer.objects.get(id=answer_id)
                is_correct = answer.is_correct
                
                if is_correct:
                    participant = QuizParticipant.objects.get(session=session, name=participant_name)
                    participant.score += 1
                    participant.save()
                
                return JsonResponse({'is_correct': is_correct})
            
            elif action == 'end_session':
                session.status = 'completed'
                session.save()
                
                participants = session.participants.all().order_by('-score')
                results = [{'name': p.name, 'score': p.score} for p in participants]
                
                return JsonResponse({'results': results})
            
            elif action == 'update_status':
                new_status = data.get('status')
                if new_status in ['waiting', 'in_progress', 'completed']:
                    session.status = new_status
                    session.save()
                    return JsonResponse({'status': 'updated'})
                else:
                    return JsonResponse({'error': '無効なステータス'}, status=400)
            
            else:
                return JsonResponse({'error': '不明なアクション。'}, status=400)
        
        except QuizSession.DoesNotExist:
            return JsonResponse({'error': 'セッションが見つかりません。'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'POSTリクエストのみ許可されています。'}, status=405)
