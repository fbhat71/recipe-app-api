"""
Test the recipe API
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Recipe,
    Tag
)
from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)

RECIPES_URL = 'recipe:recipe-list'


def detail_url(recipe_id):
    """Return recipe detail URL"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_recipe(user, **params):
    """Create and return a sample recipe"""
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': Decimal('5.00'),
        'description': 'Sample description',
        'link': 'http://www.example.com/recipe.pdf',
    }
    defaults.update(params)

    return Recipe.objects.create(user=user, **defaults)


def create_user(**params):
    """Create and return a sample user"""
    return get_user_model().objects.create_user(**params)


class PublicRecipeApiTests(TestCase):
    """Test unauthenticated recipe API access"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required"""
        response = self.client.get(reverse(RECIPES_URL))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test authenticated recipe API access"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='test@example.com',
            password='testpass'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes"""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        response = self.client.get(reverse(RECIPES_URL))

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_recipes_limited_to_user(self):
        """Test retrieving recipes for user"""
        user2 = create_user(
            email='user@example.com',
            password='testpass',
        )
        create_recipe(user=user2)
        create_recipe(user=self.user)

        response = self.client.get(reverse(RECIPES_URL))

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_view_recipe_detail(self):
        """Test viewing a recipe detail"""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        response = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(response.data, serializer.data)

    def test_create_recipe(self):
        """Test creating recipe"""
        payload = {
            'title': 'Chocolate cheesecake',
            'time_minutes': 30,
            'price': Decimal('5.00'),
        }
        response = self.client.post(reverse(RECIPES_URL), payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=response.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))
        self.assertEqual(recipe.user, self.user)

    def test_partial_update_recipe(self):
        """Test updating a recipe with patch"""
        original_link = 'http://www.example.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            link=original_link,
            title='Sample recipe',
        )
        payload = {'title': 'Chocolate cheesecake'}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update_recipe(self):
        """Test updating a recipe with put"""
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe',
            time_minutes=10,
            price=Decimal('5.00'),
            description='Sample description',
            link='http://www.example.com/recipe.pdf',
        )
        payload = {
            'title': 'Chocolate cheesecake',
            'time_minutes': 30,
            'price': Decimal('10.00'),
            'description': 'Updated description',
            'link': 'http://www.example.com/recipe2.pdf',
        }
        url = detail_url(recipe.id)
        self.client.put(url, payload)

        recipe.refresh_from_db()
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))
        self.assertEqual(recipe.user, self.user)

    def test_recipe_str(self):
        """Test the recipe string representation"""
        recipe = create_recipe(user=self.user)
        self.assertEqual(str(recipe), recipe.title)

    def test_delete_recipe(self):
        """Test deleting a recipe"""
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_update_user_returns_error(self):
        """Test updating a recipe with different user"""
        user2 = create_user(email='user2@example.com', password='testpass')
        recipe = create_recipe(user=self.user)

        payload = {'user': user2.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_recipe_other_users_recipe_error(self):
        """Test retrieving other users recipe returns error"""
        user2 = create_user(email='user2@example.com', password='testpass')
        recipe = create_recipe(user=user2)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        """Test creating a recipe with new tags"""
        payload = {
            'title': 'Thai prawn curry',
            'time_minutes': 60,
            'price': Decimal('2.50'),
            'tags': [{'name': 'Thai'}, {'name': 'Dinner'}]
        }

        res = self.client.post(reverse(RECIPES_URL), payload, format='json')
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tag(self):
        """Test creating recipe with existing tag"""
        tag_indian = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title': 'Pongal',
            'time_minutes': 60,
            'price': Decimal('4.50'),
            'tags': [{'name': 'Indian'}, {'name': 'Breakfast'}]
        }

        res = self.client.post(reverse(RECIPES_URL), payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test creating tag when updating the recipe"""
        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """Test assigning an existing tag when updating a recipe."""
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """Test clearing recipe tags"""
        tag = Tag.objects.create(user=self.user, name="Dessert")
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {
            'tags': []
        }

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)
