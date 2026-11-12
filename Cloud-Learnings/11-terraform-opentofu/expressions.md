← [Previous: Variables & Outputs](./variables-outputs.md) | [Home](../README.md) | [Next: Providers →](./providers.md)

---

# Expressions, Functions, and Meta-Arguments

---

## count

`count` creates N copies of a resource. Access each instance with `count.index`.

```hcl
# Create 3 subnets
resource "aws_subnet" "private" {
  count = 3

  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index}.0/24"
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name = "private-subnet-${count.index}"
  }
}

# Reference all: aws_subnet.private[*].id → ["subnet-aa", "subnet-bb", "subnet-cc"]
# Reference one: aws_subnet.private[0].id

# Conditional resource (create 0 or 1)
resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? 1 : 0
  domain = "vpc"
}

output "nat_ip" {
  value = var.enable_nat_gateway ? aws_eip.nat[0].public_ip : null
}
```

---

## for_each

`for_each` creates one instance per map/set element. Better than `count` when you need stable resource addressing — deleting a middle element doesn't shift indices.

```hcl
# Map: key → configuration
locals {
  subnets = {
    "us-east-1a" = "10.0.0.0/24"
    "us-east-1b" = "10.0.1.0/24"
    "us-east-1c" = "10.0.2.0/24"
  }
}

resource "aws_subnet" "private" {
  for_each = local.subnets

  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value     # map value
  availability_zone = each.key       # map key

  tags = {
    Name = "private-${each.key}"
  }
}
# Reference: aws_subnet.private["us-east-1a"].id

# Set of strings (key = value)
resource "aws_security_group_rule" "allow_ports" {
  for_each = toset(["80", "443", "8080"])

  type              = "ingress"
  from_port         = tonumber(each.key)
  to_port           = tonumber(each.key)
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.web.id
}

# for_each on list of objects
locals {
  users = [
    { name = "alice", admin = true },
    { name = "bob",   admin = false },
  ]
}

resource "aws_iam_user" "this" {
  for_each = { for u in local.users : u.name => u }

  name = each.key
  tags = { Admin = tostring(each.value.admin) }
}
```

---

## dynamic Blocks

Use `dynamic` when a nested block needs to be repeated based on a collection.

```hcl
variable "ingress_rules" {
  type = list(object({
    port        = number
    description = string
    cidr_blocks = list(string)
  }))
  default = [
    { port = 80,  description = "HTTP",  cidr_blocks = ["0.0.0.0/0"] },
    { port = 443, description = "HTTPS", cidr_blocks = ["0.0.0.0/0"] },
    { port = 22,  description = "SSH",   cidr_blocks = ["10.0.0.0/8"] },
  ]
}

resource "aws_security_group" "web" {
  name   = "web-sg"
  vpc_id = aws_vpc.main.id

  dynamic "ingress" {
    for_each = var.ingress_rules
    content {
      from_port   = ingress.value.port
      to_port     = ingress.value.port
      protocol    = "tcp"
      description = ingress.value.description
      cidr_blocks = ingress.value.cidr_blocks
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

---

## for Expressions

```hcl
# List comprehension
locals {
  # Transform: uppercase all environment names
  env_upper = [for e in var.environments : upper(e)]

  # Filter: only production CIDRs
  prod_cidrs = [for cidr in var.cidrs : cidr if cidr != "10.99.0.0/24"]

  # Map comprehension
  instance_arns = { for id, inst in aws_instance.web : id => inst.arn }

  # Flatten list of lists
  all_ports = flatten([for rule in var.rules : rule.ports])
}
```

---

## Conditional Expressions

```hcl
locals {
  # Ternary
  instance_type = var.environment == "production" ? "t3.large" : "t3.small"

  # Coalesce (first non-null)
  name = coalesce(var.custom_name, local.default_name)

  # Try (return fallback if expression throws an error)
  parsed_json = try(jsondecode(var.json_config), {})

  # Can (returns bool — true if expression succeeds)
  valid_cidr = can(cidrhost(var.cidr_block, 0))
}
```

---

## Built-in Functions

```hcl
locals {
  # String functions
  upper_env    = upper(var.environment)           # "PRODUCTION"
  trimmed      = trimspace("  hello  ")           # "hello"
  formatted    = format("%-10s %s", "name:", var.environment)
  replaced     = replace(var.name, "_", "-")
  split_list   = split(",", "a,b,c")              # ["a","b","c"]
  joined       = join(", ", ["a", "b", "c"])      # "a, b, c"
  starts       = startswith(var.name, "my-app")

  # Collection functions
  merged_maps  = merge(local.common_tags, { Extra = "tag" })
  flat_list    = flatten([[1, 2], [3, 4]])         # [1, 2, 3, 4]
  keyed        = zipmap(["a","b"], [1, 2])          # {a=1, b=2}
  length_check = length(var.subnets) > 0
  first_item   = element(var.list, 0)
  set_from_list = toset(["a", "b", "a"])            # {"a","b"}
  distinct_list = distinct(["a", "b", "a"])         # ["a","b"]

  # Numeric
  max_count = max(var.min_count, 1)
  min_count = min(var.max_count, 100)

  # Encoding
  b64_value    = base64encode("hello world")
  json_string  = jsonencode({ key = "value" })
  json_parsed  = jsondecode("{\"key\":\"value\"}")

  # Filesystem (only at plan time)
  file_content = file("${path.module}/scripts/init.sh")
  tpl_rendered = templatefile("${path.module}/templates/config.tpl", {
    db_host = aws_db_instance.main.endpoint
  })

  # Hash
  content_hash = sha256(local.file_content)
  name_hash    = md5(var.bucket_name)

  # Type conversion
  str_count    = tostring(var.instance_count)
  num_count    = tonumber("3")
}
```

---

## Preconditions and Postconditions

```hcl
# Check conditions at apply time (not plan)
resource "aws_instance" "web" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type

  lifecycle {
    precondition {
      condition     = data.aws_ami.ubuntu.architecture == "x86_64"
      error_message = "AMI must be x86_64 architecture."
    }

    postcondition {
      condition     = self.public_ip != ""
      error_message = "Instance must have a public IP."
    }
  }
}

# Check block (validates state after plan/apply, does not block)
check "alb_healthy" {
  data "aws_lb" "this" {
    arn = aws_lb.main.arn
  }

  assert {
    condition     = data.aws_lb.this.state == "active"
    error_message = "Load balancer is not in active state."
  }
}
```

---

## References

- [Expressions](https://developer.hashicorp.com/terraform/language/expressions)
- [Functions reference](https://developer.hashicorp.com/terraform/language/functions)
- [Custom conditions](https://developer.hashicorp.com/terraform/language/expressions/custom-conditions)

---

← [Previous: Variables & Outputs](./variables-outputs.md) | [Home](../README.md) | [Next: Providers →](./providers.md)
