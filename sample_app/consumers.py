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
        message_type = content.get('type')
        
        if message_type == 'participant_joined':
            # Handle participant joining
            participant_name = content.get('name')
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
            await self.update_session_question(question_index)
            question_data = await self.get_question_data(question_index)
            await self.channel_layer.group_send(
                self.session_group_name,
                {
                    'type': 'question_start',
                    'question': question_data
                }
            )
        elif message_type == 'answer_submitted':
            # Handle answer submission
            participant_name = content.get('name')
            answer_id = content.get('answer_id')
            is_correct = await self.check_answer(answer_id)
            if is_correct:
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
            await self.channel_layer.group_send(
                self.session_group_name,
                {
                    'type': 'question_end',
                    'correct_answer': content.get('correct_answer')
                }
            )
        elif message_type == 'session_end':
            # Handle ending the session
            await self.update_session_status('completed')
            await self.channel_layer.group_send(
                self.session_group_name,
                {
                    'type': 'session_end',
                    'results': await self.get_session_results()
                }
            )
    
    async def participant_joined(self, event):
        await self.send_json({
            'type': 'participant_joined',
            'name': event['name']
        })
    
    async def question_start(self, event):
        await self.send_json({
            'type': 'question_start',
            'question': event['question']
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
        session = QuizSession.objects.get(session_id=self.session_id)
        questions = QuizQuestion.objects.filter(category=session.category)
        if question_index < questions.count():
            question = questions[question_index]
            answers = question.answers.all()
            return {
                'id': question.id,
                'text': question.question_text,
                'answers': [{'id': answer.id, 'text': answer.answer_text} for answer in answers]
            }
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
