resource "aws_ecr_repository" "this" {
  name                 = var.project_name
  image_tag_mutability = "IMMUTABLE" # OTHER PERSON CANT UPDATE THE IMAGE
  force_delete         = true        # Can delete images by destroying the ecr repository

  image_scanning_configuration {
    scan_on_push = true # scan for security vulnerabilities on the image before pushing it to the repository
  }

  tags = local.tags
}

resource "aws_ecr_lifecycle_policy" "this" {
  repository = aws_ecr_repository.this.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = {
        type = "expire"
      }
    }]
  })
}
