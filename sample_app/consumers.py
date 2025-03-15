import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import QuizSession, QuizParticipant, QuizQuestion, QuizAnswer

class QuizConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.session_group_name = f'quiz_{self.session_id}'
        
        # Join session group
        await self.channel_layer.group_add(
            self.session_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave session group
        await self.channel_layer.group_discard(
            self.session_group_name,
            self.channel_name
        )
    
    async def receive_json(self, content):
        try:
            message_type = content.get('type')
            print(f"Received message type: {message_type}")
            
            if message_type == 'participant_joined':
                # Handle participant joining
                participant_name = content.get('name')
                print(f"Participant joined: {participant_name}")
                await self.channel_layer.group_send(
                    self.session_group_name,
                    {
                        'type': 'participant_joined',
                        'name': participant_name
                    }
                )
            elif message_type == 'question_start':
                # Handle starting a question
                question_index = content.get('question_index')
                print(f"Starting question {question_index}")
                
                # UI sends 1-indexed values, but backend uses 0-indexed
                # Convert to 0-indexed for database queries
                backend_index = question_index
                if backend_index >= 1:
                    # If we're on question 1 (UI), we want to show question 1 (backend index 0)
                    # If we're on question 2 (UI), we want to show question 2 (backend index 1)
                    backend_index = question_index
                
                print(f"Using backend index {backend_index} for question data retrieval")
                await self.update_session_question(backend_index)
                question_data = await self.get_question_data(backend_index)
                
                if question_data:
                    print(f"Sending question data for index {backend_index}")
                    await self.channel_layer.group_send(
                        self.session_group_name,
                        {
                            'type': 'question_start',
                            'question': question_data,
                            'question_index': backend_index
                        }
                    )
                else:
                    print(f"No question data found for index {backend_index}")
            elif message_type == 'answer_submitted':
                # Handle answer submission
                participant_name = content.get('name')
                answer_id = content.get('answer_id')
                print(f"Answer submitted by {participant_name}, answer_id: {answer_id}")
                is_correct = await self.check_answer(answer_id)
                if is_correct:
                    print(f"Correct answer by {participant_name}")
                    await self.update_participant_score(participant_name)
                await self.channel_layer.group_send(
                    self.session_group_name,
                    {
                        'type': 'answer_submitted',
                        'name': participant_name,
                        'is_correct': is_correct
                    }
                )
            elif message_type == 'question_end':
                # Handle ending a question
                print(f"Ending question")
                await self.channel_layer.group_send(
                    self.session_group_name,
                    {
                        'type': 'question_end',
                        'correct_answer': content.get('correct_answer')
                    }
                )
            elif message_type == 'session_end':
                # Handle ending the session
                print(f"Ending session")
                await self.update_session_status('completed')
                results = await self.get_session_results()
                print(f"Session results: {results}")
                await self.channel_layer.group_send(
                    self.session_group_name,
                    {
                        'type': 'session_end',
                        'results': results
                    }
                )
            else:
                print(f"Unknown message type: {message_type}")
        except Exception as e:
            print(f"Error in receive_json: {str(e)}")
            import traceback
            traceback.print_exc()
    
    async def participant_joined(self, event):
        await self.send_json({
            'type': 'participant_joined',
            'name': event['name']
        })
    
    async def question_start(self, event):
        print(f"Sending question_start message: {event}")
        await self.send_json({
            'type': 'question_start',
            'question': event['question'],
            'question_index': event.get('question_index', 0)
        })
    
    async def answer_submitted(self, event):
        await self.send_json({
            'type': 'answer_submitted',
            'name': event['name'],
            'is_correct': event['is_correct']
        })
    
    async def question_end(self, event):
        await self.send_json({
            'type': 'question_end',
            'correct_answer': event['correct_answer']
        })
    
    async def session_end(self, event):
        await self.send_json({
            'type': 'session_end',
            'results': event['results']
        })
    
    @database_sync_to_async
    def update_session_question(self, question_index):
        session = QuizSession.objects.get(session_id=self.session_id)
        session.current_question = question_index
        session.save()
    
    @database_sync_to_async
    def update_session_status(self, status):
        session = QuizSession.objects.get(session_id=self.session_id)
        session.status = status
        session.save()
    
    @database_sync_to_async
    def get_question_data(self, question_index):
        try:
            session = QuizSession.objects.get(session_id=self.session_id)
            questions = QuizQuestion.objects.filter(category=session.category)
            
            print(f"Found {questions.count()} questions for category {session.category.name}")
            
            if question_index < questions.count():
                question = questions[question_index]
                answers = question.answers.all()
                
                print(f"Question {question_index}: {question.question_text}")
                print(f"Found {answers.count()} answers")
                
                return {
                    'id': question.id,
                    'text': question.question_text,
                    'answers': [{'id': answer.id, 'text': answer.answer_text} for answer in answers]
                }
            print(f"Question index {question_index} out of range (total: {questions.count()})")
            return None
        except Exception as e:
            print(f"Error in get_question_data: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    @database_sync_to_async
    def check_answer(self, answer_id):
        answer = QuizAnswer.objects.get(id=answer_id)
        return answer.is_correct
    
    @database_sync_to_async
    def update_participant_score(self, participant_name):
        session = QuizSession.objects.get(session_id=self.session_id)
        participant = QuizParticipant.objects.get(session=session, name=participant_name)
        participant.score += 1
        participant.save()
    
    @database_sync_to_async
    def get_session_results(self):
        session = QuizSession.objects.get(session_id=self.session_id)
        participants = session.participants.all().order_by('-score')
        return [{'name': participant.name, 'score': participant.score} for participant in participants]
